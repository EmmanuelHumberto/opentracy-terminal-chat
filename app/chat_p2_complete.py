# ---------------------------------------------------------------------------
# Utilitarios de captura
# ---------------------------------------------------------------------------


def _perguntar_opcao(mensagem: str, opcoes: list[str], default: str = "") -> str:
    """Pergunta ao usuario qual opcao deseja."""
    opcoes_str = "(" + "/".join(opcoes) + ")"
    if default:
        prompt = f"{mensagem} {opcoes_str} [{default}]: "
    else:
        prompt = f"{mensagem} {opcoes_str}: "

    _console.print()
    _console.print(f"[bold yellow]{prompt}[/]", end="")
    resposta = input().strip().lower()

    if not resposta and default:
        return default

    if resposta in opcoes:
        return resposta

    _console.print(f"[red]Opcao invalida. Escolha entre: {', '.join(opcoes)}[/]")
    return _perguntar_opcao(mensagem, opcoes, default)


def _validar_snapshots(snapshots: list[dict]) -> tuple[list[dict], list[dict]]:
    """Valida integridade dos snapshots.

    Returns:
        (snapshots_validos, snapshots_rejeitados)
    """
    validos = []
    rejeitados = []

    for s in snapshots:
        erros = []

        tipo = s.get("type")
        if not tipo:
            erros.append("sem tipo")
            rejeitados.append(s)
            continue

        if s.get("timestamp_us") is None:
            erros.append("sem timestamp")

        if tipo == "hall_snapshot":
            if not isinstance(s.get("frequency_hz"), (int, float)):
                erros.append("frequency_hz invalido")
        elif tipo == "power_snapshot":
            if not isinstance(s.get("bus_voltage_mv"), (int, float)):
                erros.append("bus_voltage_mv invalido")
        elif tipo == "vibration_snapshot":
            if not isinstance(s.get("rms_norm_mg"), (int, float)):
                erros.append("rms_norm_mg invalido")
        elif tipo == "course_snapshot":
            if not isinstance(s.get("course_mm"), (int, float)):
                erros.append("course_mm invalido")

        if erros:
            s["_erros_validacao"] = erros
            rejeitados.append(s)
        else:
            validos.append(s)

    return validos, rejeitados


def _verificar_conexao_serial(porta: str, baudrate: int) -> bool:
    """Verifica se a porta serial esta acessivel."""
    import os
    try:
        return os.path.exists(porta)
    except Exception:
        return False


def _executar_captura_com_tratamento(
    config: Any,
    repo: Any,
    sessao_id: str,
) -> Optional[dict]:
    """Executa a captura com tratamento de erros e opcoes pos-falha.

    Returns:
        dict com resultado ou None se cancelado
    """
    from app.captura_serial import capturar

    if not _verificar_conexao_serial(config.porta_serial, config.baudrate):
        print_error(f"Porta serial nao encontrada: {config.porta_serial}")
        print_info("Verifique se o cabo USB esta conectado e o firmware esta rodando.")

        opcao = _perguntar_opcao(
            "Deseja tentar novamente ou cancelar?",
            ["tentar", "cancelar"],
            "tentar",
        )
        if opcao == "tentar":
            return _executar_captura_com_tratamento(config, repo, sessao_id)
        return None

    print_inicio_captura(config)
    inicio = time.monotonic()

    snapshots_brutos: list[dict] = []
    falha_critica = False
    motivo_falha = ""

    try:
        def callback(snapshot):
            snapshots_brutos.append(snapshot)
            if not config.verticais or snapshot.get("type") in config.verticais:
                print_snapshot_capturado(snapshot)

        snapshots_brutos = capturar(
            porta=config.porta_serial,
            baudrate=config.baudrate,
            duracao_seg=config.duracao_seg,
            callback=callback,
        )
    except KeyboardInterrupt:
        print_info("\n\nCaptura interrompida pelo usuario.")
    except FileNotFoundError:
        falha_critica = True
        motivo_falha = f"Porta serial {config.porta_serial} nao encontrada ou desconectada."
        print_error(f"\n{motivo_falha}")
    except PermissionError:
        falha_critica = True
        motivo_falha = f"Sem permissao de acesso a porta serial {config.porta_serial}."
        print_error(f"\n{motivo_falha}")
    except Exception as exc:
        falha_critica = True
        motivo_falha = f"Erro inesperado: {exc}"
        print_error(f"\n{motivo_falha}")

    duracao = time.monotonic() - inicio
    print_fim_captura(len(snapshots_brutos), duracao)

    if snapshots_brutos:
        print_info("Validando integridade dos snapshots...")
        validos, rejeitados = _validar_snapshots(snapshots_brutos)
        if rejeitados:
            print_error(f"{len(rejeitados)} snapshots rejeitados na validacao.")
            for r in rejeitados[:5]:
                erros = r.get("_erros_validacao", [])
                print_info(f"  - tipo={r.get('type', '?')}: {', '.join(erros)}")
        print_info(f"  {len(validos)} validos, {len(rejeitados)} rejeitados")
    else:
        validos = []
        rejeitados = []

    if falha_critica or not validos:
        print_info("\nNenhum dado valido foi capturado.")

        opcao = _perguntar_opcao(
            "O que deseja fazer?",
            ["descartar", "repetir", "salvar_parciais"],
            "repetir",
        )

        if opcao == "descartar":
            asyncio.run(repo.deletar_sessao(sessao_id))
            print_info("Dados descartados. Sessao removida do banco.")
            return None

        elif opcao == "repetir":
            print_info("Repetindo medicao... (cabecalho preservado)")
            return _executar_captura_com_tratamento(config, repo, sessao_id)

        elif opcao == "salvar_parciais":
            print_info("Salvando dados parciais...")
            if validos:
                print_info(f"  {len(validos)} snapshots salvos como parciais")
                print_info("  Execute /medicao para ver a sessao")
            return None

    return {
        "snapshots": validos,
        "rejeitados": rejeitados,
        "sessao_id": sessao_id,
        "duracao": duracao,
    }

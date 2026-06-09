# ---------------------------------------------------------------------------
# Utilitarios de captura
# ---------------------------------------------------------------------------

def _perguntar_opcao(mensagem, opcoes, default=""):
    opcoes_str = "(" + "/".join(opcoes) + ")"
    prompt = f"{mensagem} {opcoes_str} [{default}]: " if default else f"{mensagem} {opcoes_str}: "
    _console.print()
    _console.print(f"[bold yellow]{prompt}[/]", end="")
    resposta = input().strip().lower()
    if not resposta and default:
        return default
    if resposta in opcoes:
        return resposta
    _console.print(f"[red]Opcao invalida. Escolha entre: {', '.join(opcoes)}[/]")
    return _perguntar_opcao(mensagem, opcoes, default)

def _validar_snapshots(snapshots):
    validos, rejeitados = [], []
    for s in snapshots:
        erros = []
        tipo = s.get("type")
        if not tipo:
            erros.append("sem tipo")
            rejeitados.append(s)
            continue
        if s.get("timestamp_us") is None:
            erros.append("sem timestamp")
        if tipo == "hall_snapshot" and not isinstance(s.get("frequency_hz"), (int, float)):
            erros.append("frequency_hz invalido")
        elif tipo == "power_snapshot" and not isinstance(s.get("bus_voltage_mv"), (int, float)):
            erros.append("bus_voltage_mv invalido")
        elif tipo == "vibration_snapshot" and not isinstance(s.get("rms_norm_mg"), (int, float)):
            erros.append("rms_norm_mg invalido")
        elif tipo == "course_snapshot" and not isinstance(s.get("course_mm"), (int, float)):
            erros.append("course_mm invalido")
        if erros:
            s["_erros_validacao"] = erros
            rejeitados.append(s)
        else:
            validos.append(s)
    return validos, rejeitados

def _verificar_conexao_serial(porta, baudrate):
    import os
    try:
        return os.path.exists(porta)
    except Exception:
        return False

def _executar_captura_com_tratamento(config, repo, sessao_id):
    from app.captura_serial import capturar
    if not _verificar_conexao_serial(config.porta_serial, config.baudrate):
        print_error(f"Porta serial nao encontrada: {config.porta_serial}")
        print_info("Verifique se o cabo USB esta conectado e o firmware esta rodando.")
        opcao = _perguntar_opcao("Deseja tentar novamente ou cancelar?", ["tentar", "cancelar"], "tentar")
        if opcao == "tentar":
            return _executar_captura_com_tratamento(config, repo, sessao_id)
        return None
    print_inicio_captura(config)
    inicio = time.monotonic()
    snapshots_brutos = []
    falha_critica = False
    try:
        def callback(snapshot):
            snapshots_brutos.append(snapshot)
            if not config.verticais or snapshot.get("type") in config.verticais:
                print_snapshot_capturado(snapshot)
        snapshots_brutos = capturar(porta=config.porta_serial, baudrate=config.baudrate, duracao_seg=config.duracao_seg, callback=callback)
    except KeyboardInterrupt:
        print_info("\n\nCaptura interrompida pelo usuario.")
    except FileNotFoundError:
        falha_critica = True
        print_error(f"\nPorta serial {config.porta_serial} nao encontrada.")
    except PermissionError:
        falha_critica = True
        print_error(f"\nSem permissao para {config.porta_serial}.")
    except Exception as exc:
        falha_critica = True
        print_error(f"\nErro: {exc}")
    duracao = time.monotonic() - inicio
    print_fim_captura(len(snapshots_brutos), duracao)
    if snapshots_brutos:
        print_info("Validando integridade dos snapshots...")
        validos, rejeitados = _validar_snapshots(snapshots_brutos)
        if rejeitados:
            print_error(f"{len(rejeitados)} snapshots rejeitados.")
        print_info(f"  {len(validos)} validos, {len(rejeitados)} rejeitados")
    else:
        validos, rejeitados = [], []
    if falha_critica or not validos:
        print_info("\nNenhum dado valido foi capturado.")
        opcao = _perguntar_opcao("O que deseja fazer?", ["descartar", "repetir", "salvar_parciais"], "repetir")
        if opcao == "descartar":
            asyncio.run(repo.deletar_sessao(sessao_id))
            print_info("Dados descartados.")
            return None
        elif opcao == "repetir":
            print_info("Repetindo medicao...")
            return _executar_captura_com_tratamento(config, repo, sessao_id)
        elif opcao == "salvar_parciais":
            print_info("Salvando dados parciais...")
            return None
    return {"snapshots": validos, "rejeitados": rejeitados, "sessao_id": sessao_id, "duracao": duracao}

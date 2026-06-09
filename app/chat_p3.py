
def _cmd_capturar(*, ctx: ChatContext, args: str, **_: Any) -> bool:
    """Inicia captura de metricas da maquina via serial."""
    from app.captura_serial import SessaoConfig
    from app.formulario_coleta import preencher_configuracao
    from app.laudo_tecnico import gerar_diagnostico, gerar_laudo_markdown, salvar_laudo
    from app.repositorio_medicoes import RepositorioMedicoesPG

    porta = args.strip() or "/dev/ttyACM0"

    try:
        config = preencher_configuracao(porta)
    except KeyboardInterrupt:
        print_info("Captura cancelada.")
        return True

    sessao_id = datetime.now().strftime("med_%Y%m%d_%H%M%S")
    repo = RepositorioMedicoesPG(ctx.config.banco)

    try:
        asyncio.run(repo.conectar())
        asyncio.run(repo.criar_sessao_com_config(sessao_id, config))

        resultado = _executar_captura_com_tratamento(config, repo, sessao_id)

        if resultado is None:
            print_info("Operacao finalizada sem gerar laudo.")
            asyncio.run(repo.desconectar())
            return True

        if "snapshots" in resultado:
            validos = resultado["snapshots"]
            diagnostico = gerar_diagnostico(validos, config)
            asyncio.run(repo.finalizar_sessao(
                sessao_id,
                diagnostico["aprovado"],
                json.dumps(diagnostico, ensure_ascii=False, default=str),
            ))

            print_diagnostico_completo(diagnostico)

            laudo_dir = ctx.base_dir / "reports" / "laudos"
            laudo_md = gerar_laudo_markdown(sessao_id, config, validos, diagnostico)
            caminho_laudo = salvar_laudo(laudo_md, sessao_id, laudo_dir)
            print_laudo_salvo(str(caminho_laudo))

        asyncio.run(repo.desconectar())

    except Exception as exc:
        print_error(f"Erro no fluxo de captura: {exc}")
        try:
            asyncio.run(repo.desconectar())
        except Exception:
            pass
        return True

    return True


def _cmd_medicoes(*, ctx: ChatContext, **_: Any) -> bool:
    """Lista sessoes de medicao salvas."""
    from app.repositorio_medicoes import RepositorioMedicoesPG
    from app.renderer import _console
    from rich.table import Table

    repo = RepositorioMedicoesPG(ctx.config.banco)

    try:
        asyncio.run(repo.conectar())
        sessoes = asyncio.run(repo.listar_sessoes())
        asyncio.run(repo.desconectar())
    except Exception as exc:
        print_error(f"Erro ao listar sessoes: {exc}")
        return True

    if not sessoes:
        print_info("Nenhuma sessao de medicao encontrada.")
        return True

    table = Table(title="Sessoes de Medicao", box=None, show_header=True)
    table.add_column("ID", style="bold cyan", width=22)
    table.add_column("Fabricante", width=14)
    table.add_column("Modelo", width=18)
    table.add_column("Tipo", width=12)
    table.add_column("Snapshots", justify="right", width=10)
    table.add_column("Status", width=10)
    table.add_column("Data", width=20)

    for s in sessoes:
        status = "✅" if s.get("aprovado") else "❌" if s.get("aprovado") == 0 else "⏳"
        table.add_row(
            s["id"][:20],
            s.get("fabricante") or "-",
            s.get("modelo") or "-",
            s.get("tipo_coleta") or "-",
            str(s.get("total_snapshots", 0)),
            status,
            (s.get("created_at") or "-")[:19],
        )

    _console.print()
    _console.print(table)
    _console.print()
    print_info("Use /medicao <id> para ver detalhes ou /laudo <id> para gerar laudo.")
    return True


def _cmd_medicao(*, ctx: ChatContext, args: str, **_: Any) -> bool:
    """Mostra detalhes de uma sessao de medicao."""
    if not args:
        print_error("Uso: /medicao <id_da_sessao>")
        return True

    from app.repositorio_medicoes import RepositorioMedicoesPG
    from app.renderer import _console
    from rich.table import Table
    from rich.panel import Panel

    repo = RepositorioMedicoesPG(ctx.config.banco)

    try:
        asyncio.run(repo.conectar())
        sessao = asyncio.run(repo.buscar_sessao(args.strip()))
        asyncio.run(repo.desconectar())
    except Exception as exc:
        print_error(f"Erro ao buscar sessao: {exc}")
        return True

    if not sessao:
        print_error(f"Sessao nao encontrada: {args.strip()}")
        return True

    _console.print()
    _console.print(Panel.fit(
        f"[bold]Sessao: {sessao['id']}[/]",
        border_style="cyan",
    ))

    table = Table(box=None, show_header=False)
    table.add_column("Campo", style="bold", width=20)
    table.add_column("Valor")

    for campo, valor in [
        ("Fabricante", sessao.get("fabricante")),
        ("Modelo", sessao.get("modelo")),
        ("N Serie", sessao.get("numero_serie")),
        ("Tipo Maquina", sessao.get("tipo_maquina")),
        ("Motor", sessao.get("tipo_motor")),
        ("Transmissao", sessao.get("sistema_transmissao")),
        ("Curso", f"{sessao.get('curso_nominal_mm', '-')}mm"),
        ("Tipo", sessao.get("tipo_coleta")),
        ("Peca Subst.", sessao.get("peca_substituida")),
        ("Tecnico", sessao.get("tecnico")),
        ("Duracao", f"{sessao.get('duracao_seg', 0):.1f}s"),
        ("Snapshots", str(sessao.get("total_snapshots", 0))),
        ("Hall", str(sessao.get("total_hall", 0))),
        ("Power", str(sessao.get("total_power", 0))),
        ("Vibracao", str(sessao.get("total_vibration", 0))),
        ("Curso", str(sessao.get("total_course", 0))),
        ("Aprovado", "✅ Sim" if sessao.get("aprovado") else "❌ Nao" if sessao.get("aprovado") == 0 else "⏳ Pendente"),
        ("Data", sessao.get("created_at", "")[:19]),
    ]:
        if valor is not None and valor != "" and valor != "-":
            table.add_row(campo, str(valor))

    _console.print()
    _console.print(table)
    _console.print()
    return True


def _cmd_laudo(*, ctx: ChatContext, args: str, **_: Any) -> bool:
    """Gera laudo tecnico de uma sessao."""
    if not args:
        print_error("Uso: /laudo <id_da_sessao>")
        return True

    from app.repositorio_medicoes import RepositorioMedicoesPG
    from app.laudo_tecnico import gerar_diagnostico, gerar_laudo_markdown, salvar_laudo
    from app.captura_serial import SessaoConfig

    repo = RepositorioMedicoesPG(ctx.config.banco)

    try:
        asyncio.run(repo.conectar())
        sessao = asyncio.run(repo.buscar_sessao(args.strip()))
        if not sessao:
            print_error(f"Sessao nao encontrada: {args.strip()}")
            asyncio.run(repo.desconectar())
            return True

        snapshots = asyncio.run(repo.buscar_snapshots_da_sessao(args.strip()))
        asyncio.run(repo.desconectar())
    except Exception as exc:
        print_error(f"Erro ao buscar dados: {exc}")
        return True

    if not snapshots:
        print_error("Nenhum snapshot encontrado para esta sessao.")
        return True

    config = SessaoConfig(
        fabricante=sessao.get("fabricante") or "",
        modelo=sessao.get("modelo") or "",
        numero_serie=sessao.get("numero_serie") or "",
        tipo_maquina=sessao.get("tipo_maquina") or "",
        tipo_motor=sessao.get("tipo_motor") or "",
        sistema_transmissao=sessao.get("sistema_transmissao") or "",
        curso_nominal_mm=sessao.get("curso_nominal_mm"),
        curso_min_mm=sessao.get("curso_min_mm"),
        curso_max_mm=sessao.get("curso_max_mm"),
        tipo_coleta=sessao.get("tipo_coleta") or "desempenho",
        peca_substituida=sessao.get("peca_substituida") or "",
        observacoes=sessao.get("observacoes") or "",
        tecnico=sessao.get("tecnico") or "",
        porta_serial=sessao.get("porta_serial") or "",
        baudrate=sessao.get("baudrate") or 115200,
        duracao_seg=sessao.get("duracao_seg") or 30.0,
    )

    diagnostico = gerar_diagnostico(snapshots, config)
    laudo_dir = ctx.base_dir / "reports" / "laudos"
    laudo_md = gerar_laudo_markdown(args.strip(), config, snapshots, diagnostico)
    caminho_laudo = salvar_laudo(laudo_md, args.strip(), laudo_dir)

    print_diagnostico_completo(diagnostico)
    print_laudo_salvo(str(caminho_laudo))
    return True


# ---------------------------------------------------------------------------
# Router e funcoes principais
# ---------------------------------------------------------------------------


def build_router() -> CommandRouter:
    """Constroi o roteador de comandos."""
    router = CommandRouter()
    router.register("ajuda", _cmd_ajuda, description="Mostra ajuda")
    router.register("sair", _cmd_sair, description="Encerra o programa")
    router.register("limpar", _cmd_limpar, description="Limpa a tela")
    router.register("resumo", _cmd_resumo, description="Forca atualizacao do resumo")
    router.register("memoria", _cmd_memoria, description="Status da memoria")
    router.register("novo", _cmd_novo, description="Nova sessao")
    router.register("listar", _cmd_listar, description="Lista sessoes")
    router.register("carregar", _cmd_carregar, description="Carrega sessao")
    router.register("status", _cmd_status, description="Status do OpenTracy")
    router.register("tools", _cmd_tools, description="Lista MCP tools")
    router.register("indexar", _cmd_indexar, description="Indexa documentos")
    router.register("capturar", _cmd_capturar, description="Inicia captura de metricas")
    router.register("medicoes", _cmd_medicoes, description="Lista sessoes de medicao")
    router.register("medicao", _cmd_medicao, description="Detalhes de uma sessao")
    router.register("laudo", _cmd_laudo, description="Gera laudo de uma sessao")
    return router


def run_chat_loop(ctx: ChatContext) -> None:
    """Loop principal do chat."""
    print_welcome(ctx.config.opentracy.agent_id, ctx.sessions.current_id)

    while True:
        user_input = prompt_input()
        if not user_input:
            continue

        if user_input.startswith("/"):
            cmd_parts = user_input[1:].strip().split(maxsplit=1)
            cmd_name = cmd_parts[0].lower() if cmd_parts else ""
            cmd_args = cmd_parts[1] if len(cmd_parts) > 1 else ""

            if not cmd_name:
                continue

            handler = ctx.router.get_handler(cmd_name)
            if handler:
                try:
                    should_continue = handler(ctx=ctx, args=cmd_args)
                    if not should_continue:
                        break
                except Exception as exc:
                    print_error(f"Erro no comando /{cmd_name}: {exc}")
            else:
                print_error(f"Comando desconhecido: /{cmd_name}")
                print_info("Digite /ajuda para ver os comandos disponiveis.")
        else:
            session = ctx.sessions.current
            messages = session.get_all()

            session.add_message("user", user_input)
            ctx.logger.log_event(
                event="user_message",
                session_id=ctx.sessions.current_id,
                metadata={"content_preview": user_input[:100]},
            )

            total_chars = sum(len(m.get("content", "")) for m in messages)
            if total_chars > ctx.config.memory.max_chars_before_summary:
                print_info("Memoria cheia. Resumindo...")
                _cmd_resumo(ctx=ctx)

            try:
                result = ctx.client.chat(user_input, auth_token=ctx.auth_token)
            except OpenTracyError as exc:
                print_error(f"Erro na comunicacao com OpenTracy: {exc}")
                session.add_message("assistant", f"Erro: {exc}")
                continue

            response_text = result.get("response", "")
            trace_id = result.get("trace_id")

            if trace_id:
                ctx.last_trace_id = trace_id
                if ctx.config.ui.show_trace_id:
                    print_trace_id(trace_id)

            session.add_message("assistant", response_text)
            print_assistant_message(response_text)

            ctx.logger.log_event(
                event="assistant_response",
                session_id=ctx.sessions.current_id,
                metadata={
                    "trace_id": trace_id,
                    "response_length": len(response_text),
                },
            )

    print_info("Chat encerrado.")

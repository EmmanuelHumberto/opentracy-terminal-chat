def build_router() -> CommandRouter:
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
            ctx.logger.log_event(event="user_message", session_id=ctx.sessions.current_id, metadata={"content_preview": user_input[:100]})
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
            ctx.logger.log_event(event="assistant_response", session_id=ctx.sessions.current_id, metadata={"trace_id": trace_id, "response_length": len(response_text)})
    print_info("Chat encerrado.")

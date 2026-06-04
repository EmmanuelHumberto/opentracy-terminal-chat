"""Loop principal do chat.

Coordena: input do usuario, command_router, memoria, cliente HTTP,
renderizacao e logs.
"""

from __future__ import annotations

from typing import Any, Optional

from app.command_router import CommandRouter
from app.config import Config
from app.logger import JsonlLogger
from app.memory import SessionManager
from app.opentracy_client import OpenTracyClient, OpenTracyError
from app.renderer import (
    print_assistant_message,
    print_divider,
    print_error,
    print_help,
    print_info,
    print_memory_status,
    print_session_list,
    print_status,
    print_trace_id,
    print_welcome,
    clear_screen,
    prompt_input,
)


# ---------------------------------------------------------------------------
# Contexto compartilhado
# ---------------------------------------------------------------------------


class ChatContext:
    """Estado compartilhado entre o loop de chat e os comandos."""

    def __init__(
        self,
        config: Config,
        client: OpenTracyClient,
        sessions: SessionManager,
        logger: JsonlLogger,
        router: CommandRouter,
        auth_token: str,
    ) -> None:
        self.config = config
        self.client = client
        self.sessions = sessions
        self.logger = logger
        self.router = router
        self.auth_token = auth_token
        self.last_trace_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------


def _cmd_ajuda(*, ctx: ChatContext, **_: Any) -> bool:
    print_help()
    return True


def _cmd_sair(*, ctx: ChatContext, **_: Any) -> bool:
    return False


def _cmd_limpar(*, ctx: ChatContext, **_: Any) -> bool:
    clear_screen()
    return True


def _cmd_resumo(*, ctx: ChatContext, **_: Any) -> bool:
    """Forca a geracao de resumo."""
    session = ctx.sessions.current
    messages = session.get_all()
    if not messages:
        print_info("Nenhuma mensagem para resumir.")
        return True

    previous = session.load_summary()
    recent = session.get_recent(ctx.config.memory.max_history)

    prompt_parts = [
        "Voce resume conversas tecnicas em portugues.",
        "Mantenha assunto principal, decisoes, dados tecnicos, pendencias e proximos passos.",
        f"Limite: {ctx.config.memory.summary_max_chars} caracteres, 3 paragrafos curtos.",
    ]
    if previous:
        prompt_parts.append(f"\nResumo anterior:\n{previous}")
    prompt_parts.append(f"\nNovas mensagens:\n{_format_messages(recent)}")
    prompt_parts.append("\nResumo atualizado:")

    summary_prompt = "\n".join(prompt_parts)

    print_info("Gerando resumo...")

    try:
        result = ctx.client.chat(
            summary_prompt,
            auth_token=ctx.auth_token,
        )
    except OpenTracyError as exc:
        print_error(f"Falha ao gerar resumo: {exc}")
        return True

    summary = (result.get("response") or "").strip()
    if summary:
        session.save_summary(summary)
        ctx.logger.log_memory_summary(
            session_id=ctx.sessions.current_id,
            summary_chars=len(summary),
        )
        print_info("Resumo atualizado.")
    else:
        print_error("Resumo veio vazio.")

    return True


def _cmd_memoria(*, ctx: ChatContext, **_: Any) -> bool:
    session = ctx.sessions.current
    messages = session.get_all()
    summary = session.load_summary()

    print_memory_status(
        session_id=ctx.sessions.current_id,
        message_count=len(messages),
        has_summary=summary is not None,
        history_file=str(session.history_path),
        summary_file=str(session.summary_path) if summary else None,
    )
    return True


def _cmd_novo(*, ctx: ChatContext, **_: Any) -> bool:
    sid = ctx.sessions.create_session()
    print_info(f"Nova sessao: {sid}")
    return True


def _cmd_listar(*, ctx: ChatContext, **_: Any) -> bool:
    sessions = ctx.sessions.list_sessions()
    print_session_list(sessions)
    return True


def _cmd_carregar(*, args: str, ctx: ChatContext, **_: Any) -> bool:
    if not args:
        print_error("Uso: /carregar <id_da_sessao>")
        return True
    success = ctx.sessions.load_session(args.strip())
    if success:
        print_info(f"Sessao carregada: {args.strip()}")
    else:
        print_error(f"Sessao nao encontrada: {args.strip()}")
    return True


def _cmd_status(*, ctx: ChatContext, **_: Any) -> bool:
    backend_ok = ctx.client.check_backend_health()
    runtime_ok = ctx.client.check_runtime_health()

    agent_ok = False
    try:
        agents = ctx.client.list_agents(ctx.auth_token)
        agent_ok = any(
            a.get("id") == ctx.config.opentracy.agent_id
            for a in agents
        )
    except OpenTracyError:
        pass

    token_ok = bool(ctx.auth_token)

    print_status(
        backend_ok=backend_ok,
        runtime_ok=runtime_ok,
        agent_ok=agent_ok,
        token_ok=token_ok,
        agent_id=ctx.config.opentracy.agent_id,
        last_trace=ctx.last_trace_id,
    )
    return True


# ---------------------------------------------------------------------------
# Registro de comandos
# ---------------------------------------------------------------------------


def build_router() -> CommandRouter:
    router = CommandRouter()
    router.register("ajuda", _cmd_ajuda, "Mostra lista de comandos")
    router.register("sair", _cmd_sair, "Encerra o programa")
    router.register("limpar", _cmd_limpar, "Limpa a tela")
    router.register("resumo", _cmd_resumo, "Forca atualizacao do resumo")
    router.register("memoria", _cmd_memoria, "Mostra status da memoria")
    router.register("novo", _cmd_novo, "Inicia nova sessao")
    router.register("listar", _cmd_listar, "Lista sessoes anteriores")
    router.register("carregar", _cmd_carregar, "Carrega sessao anterior")
    router.register("status", _cmd_status, "Mostra status do OpenTracy")
    return router


# ---------------------------------------------------------------------------
# Loop
# ---------------------------------------------------------------------------


def run_chat_loop(ctx: ChatContext) -> None:
    """Loop principal: le input, roteia comando ou envia para LLM."""

    session = ctx.sessions.current
    print_welcome(ctx.config.opentracy.agent_id, session.session_id)

    while True:
        user_input = prompt_input()

        if not user_input:
            continue

        # Tenta comando
        if ctx.router.is_command(user_input):
            should_continue = ctx.router.dispatch(
                user_input,
                ctx=ctx,
            )
            if not should_continue:
                break
            continue

        # --- Turno de chat ---
        session.add_message("user", user_input)

        # Carrega resumo + historico recente
        summary = session.load_summary()
        recent = session.get_recent(ctx.config.memory.max_history)

        # Verifica se precisa resumir
        estimated = session.estimated_context_chars(
            summary, recent, user_input
        )
        if estimated > ctx.config.memory.max_chars_before_summary:
            print_info(
                f"Contexto grande ({estimated} chars). "
                f"Resumindo automaticamente..."
            )
            _auto_summarize(ctx, session, summary, recent)

            # Recarrega apos resumo
            summary = session.load_summary()
            recent = session.get_recent(ctx.config.memory.max_history)

        # Monta request enriquecido
        enriched = _build_enriched_request(
            summary=summary,
            recent=recent,
            user_message=user_input,
        )

        # Prepara history para o payload HTTP
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in recent
        ]

        try:
            result = ctx.client.chat(
                enriched,
                history=history,
                auth_token=ctx.auth_token,
            )
        except OpenTracyError as exc:
            print_error(str(exc))
            ctx.logger.log_error(
                kind=f"http_{exc.status_code}" if exc.status_code else "connection",
                message=str(exc),
                session_id=ctx.sessions.current_id,
            )
            continue

        response = result.get("response") or ""
        trace_id = result.get("trace_id")
        duration_ms = result.get("duration_ms", 0)
        success = result.get("success", False)
        error = result.get("error")

        ctx.last_trace_id = trace_id

        if success:
            print_assistant_message(response)
            print_trace_id(trace_id)
            session.add_message("assistant", response, trace_id=trace_id)
        else:
            print_error(error or "Resposta veio com erro do servidor.")

        ctx.logger.log_chat(
            session_id=ctx.sessions.current_id,
            trace_id=trace_id,
            success=success,
            duration_ms=duration_ms,
            input_chars=len(enriched),
            output_chars=len(response),
        )

        print_divider()


# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------


def _build_enriched_request(
    summary: Optional[str],
    recent: list[dict[str, Any]],
    user_message: str,
) -> str:
    """Monta o request enriquecido com resumo + historico recente."""
    parts: list[str] = [
        "Voce esta em uma conversa tecnica continua.",
        "Use o resumo e as ultimas mensagens apenas como contexto.",
        "Responda a mensagem atual do usuario.",
    ]

    if summary:
        parts.append(f"\nResumo da sessao:\n{summary}")

    if recent:
        history_str = _format_messages(recent)
        parts.append(f"\nUltimas mensagens:\n{history_str}")

    parts.append(f"\nMensagem atual do usuario:\n{user_message}")

    return "\n\n".join(parts)


def _format_messages(messages: list[dict[str, Any]]) -> str:
    """Formata mensagens para inclusao no prompt."""
    lines = []
    for m in messages:
        role = m.get("role", "unknown")
        content = m.get("content", "")
        lines.append(f"{role.capitalize()}: {content}")
    return "\n".join(lines)


def _auto_summarize(
    ctx: ChatContext,
    session: Any,
    summary: Optional[str],
    recent: list[dict[str, Any]],
) -> None:
    """Gera resumo automaticamente quando o contexto fica grande."""
    prompt_parts = [
        "Voce resume conversas tecnicas em portugues.",
        "Mantenha assunto principal, decisoes, dados tecnicos, pendencias e proximos passos.",
        f"Limite: {ctx.config.memory.summary_max_chars} caracteres, 3 paragrafos curtos.",
    ]
    if summary:
        prompt_parts.append(f"\nResumo anterior:\n{summary}")
    prompt_parts.append(f"\nNovas mensagens:\n{_format_messages(recent)}")
    prompt_parts.append("\nResumo atualizado:")

    summary_prompt = "\n".join(prompt_parts)

    try:
        result = ctx.client.chat(
            summary_prompt,
            auth_token=ctx.auth_token,
        )
        new_summary = (result.get("response") or "").strip()
        if new_summary:
            session.save_summary(new_summary)
            ctx.logger.log_memory_summary(
                session_id=ctx.sessions.current_id,
                summary_chars=len(new_summary),
            )
    except OpenTracyError:
        pass  # Falha no resumo nao interrompe o chat

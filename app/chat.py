"""Loop principal do chat.

Coordena: input do usuario, command_router, memoria, cliente HTTP,
renderizacao e logs.
"""

from __future__ import annotations

from pathlib import Path
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
    print_success,
    print_trace_id,
    print_welcome,
    clear_screen,
    prompt_input,
)


# Caminho absoluto do OpenTracy (usado pelo /indexar)
OPENTRACY_ROOT = Path("/home/hiatus/Projetos/ligadotattoo/OpenTracy")


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
        self.base_dir: Path = Path(__file__).resolve().parent.parent


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
        result = ctx.client.chat(summary_prompt, auth_token=ctx.auth_token)
    except OpenTracyError as exc:
        print_error(f"Falha ao gerar resumo: {exc}")
        return True

    summary = (result.get("response") or "").strip()
    if summary:
        _apply_summary(ctx, session, summary)
        print_info("Resumo atualizado. Historico compactado.")
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
        agent_ok = any(a.get("id") == ctx.config.opentracy.agent_id for a in agents)
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


def _cmd_indexar(*, ctx: ChatContext, **_: Any) -> bool:
    """Converte documentos em knowledge/ para Markdown e ingere no CorpusStore."""
    source_dir = ctx.base_dir / ctx.config.knowledge.source_dir
    output_dir = ctx.base_dir / ctx.config.knowledge.output_dir

    if not source_dir.is_dir():
        print_error(f"Diretorio de origem nao encontrado: {source_dir}")
        print_info("Crie a pasta knowledge/ e adicione arquivos .md, .txt, .pdf, .docx ou .xlsx.")
        return True

    print_info(f"Convertendo documentos de {source_dir}...")
    try:
        from ligadoai_tools.document_server import convert_directory
        conv_result = convert_directory(source_dir, output_dir, recursive=True)
    except Exception as exc:
        print_error(f"Erro na conversao: {exc}")
        return True

    if conv_result.get("errors", 0) > 0:
        for err in conv_result.get("error_details", []):
            msg = err.get("error", {}).get("message", "desconhecido")
            print_error(f"  Erro: {msg}")
    if conv_result.get("partials", 0) > 0:
        for p in conv_result.get("partial_details", []):
            detail = p.get("partial", {}).get("detail", "")
            if detail:
                print_info(f"  Aviso: {detail}")

    converted = conv_result.get("converted", 0)
    errors = conv_result.get("errors", 0)
    partials = conv_result.get("partials", 0)
    print_info(f"Convertidos: {converted} arquivos, {errors} erros, {partials} avisos de falha parcial.")

    if converted == 0:
        print_error("Nenhum arquivo foi convertido.")
        return True

    print_info("Ingerindo no CorpusStore do OpenTracy...")
    try:
        import subprocess, sys
        chunk_size = ctx.config.knowledge.chunk_size
        overlap = ctx.config.knowledge.overlap
        ingest_target = ctx.config.knowledge.ingest_target

        opentracy_python = str(OPENTRACY_ROOT / ".venv" / "bin" / "python3")
        if not Path(opentracy_python).is_file():
            opentracy_python = str(OPENTRACY_ROOT / ".venv" / "bin" / "python")
        if not Path(opentracy_python).is_file():
            opentracy_python = "python3"

        cmd = [opentracy_python, "-m", "corpora.ingest", str(output_dir), "--chunk-size", str(chunk_size), "--overlap", str(overlap)]
        if ingest_target:
            cmd.extend(["--root", ingest_target])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=str(OPENTRACY_ROOT))
        if result.returncode == 0:
            print_success(f"Ingest concluido: {result.stdout.strip()}")
        else:
            print_error(f"Falha no ingest: {result.stderr[:500]}")
            return True
    except FileNotFoundError:
        print_error("Comando corpora.ingest nao encontrado.")
        return True
    except subprocess.TimeoutExpired:
        print_error("Timeout de 120s excedido durante ingest.")
        return True
    except Exception as exc:
        print_error(f"Erro no ingest: {exc}")
        return True

    ctx.logger.log_event(event="indexar", session_id=ctx.sessions.current_id, metadata={"converted": converted, "errors": errors, "partials": partials})
    print_success("Base de conhecimento indexada com sucesso!")
    return True


def _cmd_tools(*, ctx: ChatContext, **_: Any) -> bool:
    """Lista as MCP tools registradas no agente."""
    try:
        import httpx
        r = httpx.get(
            f"{ctx.config.opentracy.backend_url}/v1/agents/{ctx.config.opentracy.agent_id}/mcp/tools",
            headers={"Authorization": f"Bearer {ctx.auth_token}"},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            tools = data if isinstance(data, list) else data.get("tools", [])
            if not tools:
                print_info("Nenhuma MCP tool registrada.")
                return True
            from app.renderer import _console
            from rich.table import Table
            table = Table(title="MCP Tools", box=None, show_header=True)
            table.add_column("Tool", style="bold cyan")
            table.add_column("Descricao")
            for t in tools:
                # A API retorna "tool_name", "server_name" e "qualified_name"
                name = t.get("tool_name") or t.get("name") or t.get("qualified_name", "?")
                table.add_row(name, t.get("description", "-"))
            _console.print()
            _console.print(table)
            _console.print()
        else:
            print_error(f"Falha ao listar tools (HTTP {r.status_code})")
    except Exception as exc:
        print_error(f"Erro ao consultar tools: {exc}")
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
    router.register("indexar", _cmd_indexar, "Converte documentos e ingere no CorpusStore")
    router.register("tools", _cmd_tools, "Lista MCP tools registradas")
    return router


# ---------------------------------------------------------------------------
# Loop
# ---------------------------------------------------------------------------


def run_chat_loop(ctx: ChatContext) -> None:
    session = ctx.sessions.current
    print_welcome(ctx.config.opentracy.agent_id, session.session_id)

    while True:
        user_input = prompt_input()
        if not user_input:
            continue

        if ctx.router.is_command(user_input):
            should_continue = ctx.router.dispatch(user_input, ctx=ctx)
            if not should_continue:
                break
            continue

        session.add_message("user", user_input)
        summary = session.load_summary()
        recent = session.get_recent(ctx.config.memory.max_history)

        estimated = session.estimated_context_chars(summary, recent, user_input)
        msg_count = session.count_messages_since_summary()
        needs_summary = estimated > ctx.config.memory.max_chars_before_summary or msg_count > ctx.config.memory.max_history * 2

        if needs_summary:
            print_info(f"Resumindo sessao ({msg_count} mensagens, ~{estimated} chars)...")
            _auto_summarize(ctx, session, summary, recent)
            summary = session.load_summary()
            recent = session.get_recent(ctx.config.memory.max_history)

        history = [{"role": m["role"], "content": m["content"]} for m in recent]

        try:
            result = ctx.client.chat(request=user_input, history=history, auth_token=ctx.auth_token)
        except OpenTracyError as exc:
            print_error(str(exc))
            ctx.logger.log_error(kind=f"http_{exc.status_code}" if exc.status_code else "connection", message=str(exc), session_id=ctx.sessions.current_id)
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

        ctx.logger.log_chat(session_id=ctx.sessions.current_id, trace_id=trace_id, success=success, duration_ms=duration_ms, input_chars=len(user_input), output_chars=len(response))
        print_divider()


# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------


def _build_enriched_request(summary, recent, user_message):
    parts = ["Voce esta em uma conversa tecnica continua.", "Use o resumo e as ultimas mensagens apenas como contexto.", "Responda a mensagem atual do usuario."]
    if summary:
        parts.append(f"\nResumo da sessao:\n{summary}")
    if recent:
        parts.append(f"\nUltimas mensagens:\n{_format_messages(recent)}")
    parts.append(f"\nMensagem atual do usuario:\n{user_message}")
    return "\n\n".join(parts)


def _format_messages(messages):
    lines = []
    for m in messages:
        lines.append(f"{m.get('role', 'unknown').capitalize()}: {m.get('content', '')}")
    return "\n".join(lines)


def _auto_summarize(ctx, session, summary, recent):
    prompt_parts = ["Voce resume conversas tecnicas em portugues.", "Mantenha assunto principal, decisoes, dados tecnicos, pendencias e proximos passos.", f"Limite: {ctx.config.memory.summary_max_chars} caracteres, 3 paragrafos curtos."]
    if summary:
        prompt_parts.append(f"\nResumo anterior:\n{summary}")
    prompt_parts.append(f"\nNovas mensagens:\n{_format_messages(recent)}")
    prompt_parts.append("\nResumo atualizado:")
    try:
        result = ctx.client.chat("\n".join(prompt_parts), auth_token=ctx.auth_token)
        new_summary = (result.get("response") or "").strip()
        if new_summary:
            _apply_summary(ctx, session, new_summary)
    except OpenTracyError:
        pass


def _apply_summary(ctx, session, summary):
    session.save_summary(summary)
    session.trim_history_after_summary(keep_last=2)
    ctx.logger.log_memory_summary(session_id=ctx.sessions.current_id, summary_chars=len(summary))

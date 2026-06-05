"""Interface de terminal usando Rich.

Renderiza mensagens, comandos, erros e status.
"""

from __future__ import annotations

from typing import Any, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text


_console = Console()


def print_welcome(agent_id: str, session_id: str) -> None:
    _console.print()
    _console.print(Panel.fit(
        f"[bold cyan]LigadoAI Terminal Chat[/]\n"
        f"Agente: [green]{agent_id}[/]  |  Sessao: [yellow]{session_id}[/]\n\n"
        f"Digite [bold]/ajuda[/] para comandos ou [bold]/sair[/] para encerrar.",
        border_style="cyan"))
    _console.print()


def print_user_message(content: str) -> None:
    _console.print()
    _console.print(Text(f"Voce: {content}", style="bold green"))


def print_assistant_message(content: Optional[str]) -> None:
    _console.print()
    _console.print(Text("Cous:", style="bold blue"))
    if content:
        _console.print(Markdown(content))
    else:
        _console.print("[italic](resposta vazia)[/]")


def print_error(message: str) -> None:
    _console.print()
    _console.print(Text(f"Erro: {message}", style="bold red"))


def print_info(message: str) -> None:
    _console.print()
    _console.print(Text(message, style="bold yellow"))


def print_success(message: str) -> None:
    _console.print()
    _console.print(Text(message, style="bold green"))


def print_divider() -> None:
    _console.print(Rule(style="dim"))


def print_help() -> None:
    table = Table(title="Comandos", box=None, show_header=False)
    table.add_column("Comando", style="bold cyan", width=18)
    table.add_column("Descricao")
    for cmd, desc in [
        ("/ajuda", "Mostra esta ajuda"),
        ("/sair", "Encerra o programa"),
        ("/limpar", "Limpa a tela"),
        ("/resumo", "Forca atualizacao do resumo"),
        ("/memoria", "Mostra status da memoria"),
        ("/novo", "Inicia nova sessao"),
        ("/listar", "Lista sessoes anteriores"),
        ("/carregar <id>", "Carrega sessao anterior"),
        ("/status", "Mostra status do OpenTracy"),
        ("/tools", "Lista MCP tools registradas"),
        ("/indexar", "Converte documentos e ingere"),
    ]:
        table.add_row(cmd, desc)
    _console.print()
    _console.print(table)
    _console.print()


def print_memory_status(session_id, message_count, has_summary, history_file, summary_file=None):
    table = Table(title="Memoria", box=None, show_header=False)
    table.add_column("Campo", style="bold", width=20)
    table.add_column("Valor")
    table.add_row("Sessao", session_id)
    table.add_row("Mensagens", str(message_count))
    table.add_row("Tem resumo", "Sim" if has_summary else "Nao")
    table.add_row("Historico", history_file)
    if summary_file:
        table.add_row("Resumo", summary_file)
    _console.print()
    _console.print(table)
    _console.print()


def print_status(backend_ok, runtime_ok, agent_ok, token_ok, agent_id, last_trace=None):
    table = Table(title="Status", box=None, show_header=False)
    table.add_column("Componente", style="bold", width=20)
    table.add_column("Status")
    table.add_row("Backend", _status_str(backend_ok))
    table.add_row("Runtime", _status_str(runtime_ok))
    table.add_row(f"Agente ({agent_id})", _status_str(agent_ok))
    table.add_row("Token API", _status_str(token_ok))
    if last_trace:
        table.add_row("Ultimo trace", last_trace)
    _console.print()
    _console.print(table)
    _console.print()


def print_session_list(sessions):
    if not sessions:
        _console.print("[italic]Nenhuma sessao encontrada.[/]")
        return
    table = Table(box=None, show_header=True)
    table.add_column("ID", style="bold cyan", width=22)
    table.add_column("Mensagens", justify="right", width=10)
    table.add_column("Ultima msg", width=30)
    table.add_column("Resumo", width=6)
    for s in sessions:
        table.add_row(s["id"], str(s["message_count"]), (s.get("last_message", "") or "-")[:30], "Sim" if s.get("has_summary") else "Nao")
    _console.print()
    _console.print(table)
    _console.print()


def print_trace_id(trace_id: Optional[str]) -> None:
    if trace_id:
        _console.print()
        _console.print(Text(f"trace: {trace_id}", style="dim"))


def prompt_input() -> str:
    try:
        _console.print()
        _console.print(Text("Voce:", style="bold green"), end=" ")
        return input()
    except (EOFError, KeyboardInterrupt):
        return "/sair"


def clear_screen() -> None:
    _console.clear()


def _status_str(ok: bool) -> str:
    return "[green]OK[/]" if ok else "[red]FALHA[/]"

"""Interface de terminal moderna usando Rich.

Renderiza mensagens, comandos, erros e status com identidade visual
inspirada em interfaces de assistentes modernos — paineis estilizados,
avatares, spinner, barras de progresso e grid de comandos.
"""

from __future__ import annotations

from typing import Any, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich.spinner import Spinner
from rich.progress import BarColumn, Progress, TextColumn
from rich.align import Align
from rich.columns import Columns
from rich import box

_console = Console()


# ═══════════════════════════════════════════════════════════════════════
# Constantes de estilo
# ═══════════════════════════════════════════════════════════════════════

THEME_USER = "bold green"
THEME_ASSISTANT = "bold cyan"
THEME_ERROR = "bold red"
THEME_INFO = "bold yellow"
THEME_SUCCESS = "bold green"
THEME_DIM = "dim"
THEME_ACCENT = "bold magenta"
THEME_HIGHLIGHT = "bold white"

AVATAR_USER = "🧑"
AVATAR_ASSISTANT = "🤖"
ICON_OK = "✅"
ICON_FAIL = "❌"
ICON_WARN = "⚠️"
ICON_INFO = "ℹ️"
ICON_CLOCK = "⏳"
DIVIDER_CHAR = "◆"


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def _status_icon(ok: bool) -> str:
    return ICON_OK if ok else ICON_FAIL

def _status_style(ok: bool) -> str:
    return "green" if ok else "red"

def _divider() -> None:
    _console.print(Rule(style="dim", characters=f" {DIVIDER_CHAR} "))


# ═══════════════════════════════════════════════════════════════════════
# Boas-vindas
# ═══════════════════════════════════════════════════════════════════════

def print_welcome(agent_id: str, session_id: str, memory_pct: float = 0.0) -> None:
    """Banner de boas-vindas com arte ASCII e cards de status."""
    _console.clear()
    _console.print()
    _console.print(Align.center(Text(
        r"""
  ██████╗  ██████╗ ██╗   ██╗███████╗
 ██╔════╝ ██╔═══██╗██║   ██║██╔════╝
 ██║      ██║   ██║██║   ██║███████╗
 ██║      ██║   ██║██║   ██║╚════██║
 ╚██████╗ ╚██████╔╝╚██████╔╝███████║
  ╚═════╝  ╚═════╝  ╚═════╝ ╚══════╝
""", style="bold cyan")))
    _console.print()
    _console.print(Align.center(
        Text("Assistente Técnico para Máquinas de Tatuagem", style="dim italic")))
    _console.print()
    _divider()

    # Cards de status
    status_table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True)
    status_table.add_column(style="cyan", justify="center", width=20)
    status_table.add_column(style="cyan", justify="center", width=20)
    status_table.add_column(style="cyan", justify="center", width=20)
    status_table.add_row(
        f"Agente\n[bold white]{agent_id}[/]",
        f"Sessão\n[bold white]{session_id}[/]",
        f"Memória\n[bold white]{memory_pct:.0f}%[/]",
    )
    _console.print(Panel(status_table, border_style="cyan", title="Sistema", title_align="left"))
    _console.print()
    _console.print(Text("Digite /ajuda para comandos  •  /sair para encerrar", style="dim"))

    # Rodapé de atalhos
    _console.print()
    shortcuts = Columns([
        Text("/ajuda", style="bold cyan"),
        Text("/status", style="bold cyan"),
        Text("/capturar", style="bold cyan"),
        Text("/medicoes", style="bold cyan"),
    ], equal=True, expand=True)
    _console.print(Panel(shortcuts, border_style="dim", title="Atalhos", title_align="left"))
    _console.print()


# ═══════════════════════════════════════════════════════════════════════
# Mensagens
# ═══════════════════════════════════════════════════════════════════════

def print_user_message(content: str) -> None:
    """Mensagem do usuário: painel à direita, verde."""
    _console.print()
    panel = Panel(
        Markdown(content, style="green"),
        border_style="green",
        box=box.ROUNDED,
        title=f"{AVATAR_USER} Você",
        title_align="right",
    )
    _console.print(Align.right(panel))
    _console.print()


def print_assistant_message(content: Optional[str]) -> None:
    """Mensagem do assistente: painel à esquerda, ciano."""
    _console.print()
    if content:
        panel = Panel(
            Markdown(content),
            border_style="cyan",
            box=box.ROUNDED,
            title=f"{AVATAR_ASSISTANT} Cous",
            title_align="left",
        )
        _console.print(panel)
    else:
        _console.print(Text("(resposta vazia)", style="dim italic"))
    _console.print()


def print_thinking() -> None:
    """Spinner enquanto aguarda resposta do LLM."""
    _console.print()
    _console.print(
        Panel(
            Spinner("dots", text=" Pensando...", style="cyan"),
            border_style="dim",
            box=box.MINIMAL,
            width=30,
        )
    )


def print_thinking_done() -> None:
    """Remove o spinner após resposta (sobrescreve a linha)."""
    pass  # Rich gerencia automaticamente; o próximo print sobrescreve


# ═══════════════════════════════════════════════════════════════════════
# Status e informações
# ═══════════════════════════════════════════════════════════════════════

def print_error(message: str) -> None:
    _console.print()
    _console.print(Panel(
        Text(message, style=THEME_ERROR),
        border_style="red",
        box=box.MINIMAL,
        title=f"{ICON_FAIL} Erro",
        title_align="left",
    ))


def print_info(message: str) -> None:
    _console.print()
    _console.print(Panel(
        Text(message, style=THEME_INFO),
        border_style="yellow",
        box=box.MINIMAL,
        title=f"{ICON_INFO} Info",
        title_align="left",
    ))


def print_success(message: str) -> None:
    _console.print()
    _console.print(Panel(
        Text(message, style=THEME_SUCCESS),
        border_style="green",
        box=box.MINIMAL,
        title=f"{ICON_OK} Sucesso",
        title_align="left",
    ))


def print_warning(message: str) -> None:
    """Aviso com ícone de atenção."""
    _console.print()
    _console.print(Panel(
        Text(message, style="yellow"),
        border_style="yellow",
        box=box.MINIMAL,
        title=f"{ICON_WARN} Aviso",
        title_align="left",
    ))


def print_divider() -> None:
    _divider()


def print_trace_id(trace_id: Optional[str]) -> None:
    if trace_id:
        _console.print()
        _console.print(Text(f"  trace: {trace_id}", style="dim"))


# ═══════════════════════════════════════════════════════════════════════
# Tela de ajuda
# ═══════════════════════════════════════════════════════════════════════

_HELP_SECTIONS = [
    ("Básicos", [
        ("/ajuda", "Mostra esta ajuda"),
        ("/sair", "Encerra o programa"),
        ("/limpar", "Limpa a tela"),
        ("/status", "Status do OpenTracy"),
    ]),
    ("Memória", [
        ("/resumo", "Força atualização do resumo"),
        ("/memoria", "Mostra status da memória"),
        ("/novo", "Inicia nova sessão"),
        ("/listar", "Lista sessões anteriores"),
        ("/carregar <id>", "Carrega sessão anterior"),
    ]),
    ("Medição", [
        ("/capturar [porta]", "Inicia captura de métricas"),
        ("/medicoes", "Lista sessões de medição"),
        ("/medicao <id>", "Detalhes de uma sessão"),
        ("/laudo <id>", "Gera laudo técnico"),
    ]),
    ("Ferramentas", [
        ("/tools", "Lista MCP tools registradas"),
        ("/indexar", "Converte documentos e ingere"),
    ]),
]

def print_help() -> None:
    """Ajuda em grid de cards por seção."""
    _console.print()
    panels = []
    for section, commands in _HELP_SECTIONS:
        table = Table(box=box.SIMPLE, show_header=False, expand=True)
        table.add_column("cmd", style="bold cyan", width=18)
        table.add_column("desc", style="dim")
        for cmd, desc in commands:
            table.add_row(cmd, desc)
        panels.append(Panel(table, border_style="cyan", title=section, title_align="left"))
    _console.print(Columns(panels, equal=True))
    _console.print()


# ═══════════════════════════════════════════════════════════════════════
# Status do sistema
# ═══════════════════════════════════════════════════════════════════════

def print_status(
    backend_ok: bool,
    runtime_ok: bool,
    agent_ok: bool,
    token_ok: bool,
    agent_id: str,
    last_trace: Optional[str] = None,
) -> None:
    """Barra de status simplificada com indicadores visuais."""
    _console.print()
    items = [
        f"{_status_icon(backend_ok)} Backend",
        f"{_status_icon(runtime_ok)} Runtime",
        f"{_status_icon(agent_ok)} Agente ({agent_id})",
        f"{_status_icon(token_ok)} Token",
    ]
    if last_trace:
        items.append(f"{ICON_INFO} {last_trace}")
    _console.print(Panel(
        Text("  ".join(items), style="bold"),
        border_style=_status_style(all([backend_ok, runtime_ok, agent_ok, token_ok])),
        box=box.SIMPLE,
    ))
    _console.print()


# ═══════════════════════════════════════════════════════════════════════
# Memória
# ═══════════════════════════════════════════════════════════════════════

def print_memory_status(
    session_id: str,
    message_count: int,
    has_summary: bool,
    history_file: str,
    summary_file: Optional[str] = None,
    max_chars: int = 16000,
    current_chars: int = 0,
) -> None:
    """Status da memória com barra de progresso."""
    _console.print()
    pct = min(100.0, (current_chars / max_chars * 100.0)) if max_chars > 0 else 0.0
    bar_color = "green" if pct < 50 else "yellow" if pct < 80 else "red"

    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("Campo", style="bold", width=14)
    table.add_column("Valor")
    table.add_row("Sessão", session_id)
    table.add_row("Mensagens", str(message_count))
    table.add_row("Resumo", ICON_OK if has_summary else ICON_FAIL)
    table.add_row("Histórico", history_file)
    if summary_file:
        table.add_row("Resumo", summary_file)

    # Barra de progresso estilizada
    bar_width = 30
    filled = int(bar_width * pct / 100)
    bar = f"[{bar_color}]{'█' * filled}{'░' * (bar_width - filled)}[/]"
    table.add_row("Uso", f"{bar}  [bold {bar_color}]{pct:.0f}%[/]")

    _console.print(Panel(
        table,
        border_style=bar_color,
        box=box.ROUNDED,
        title="Memória",
        title_align="left",
    ))
    _console.print()


# ═══════════════════════════════════════════════════════════════════════
# Sessões
# ═══════════════════════════════════════════════════════════════════════

def print_session_list(sessions: list[dict]) -> None:
    """Lista de sessões em tabela estilizada."""
    if not sessions:
        _console.print()
        _console.print(Text("Nenhuma sessão encontrada.", style="dim italic"))
        return
    _console.print()
    table = Table(
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style="bold cyan",
        title="Sessões",
        title_style="bold",
    )
    table.add_column("ID", style="bold cyan", width=22)
    table.add_column("Mensagens", justify="right", width=10)
    table.add_column("Última msg", width=30)
    table.add_column("Resumo", width=6)
    for s in sessions:
        table.add_row(
            s["id"],
            str(s.get("message_count", 0)),
            (s.get("last_message", "") or "-")[:30],
            ICON_OK if s.get("has_summary") else ICON_FAIL,
        )
    _console.print(table)
    _console.print()


# ═══════════════════════════════════════════════════════════════════════
# Prompt de input
# ═══════════════════════════════════════════════════════════════════════

def prompt_input() -> str:
    """Prompt de input estilizado."""
    try:
        _console.print()
        _console.print(Text("▸", style="bold cyan"), end=" ")
        return input()
    except (EOFError, KeyboardInterrupt):
        return "/sair"


def clear_screen() -> None:
    _console.clear()


# ═══════════════════════════════════════════════════════════════════════
# Captura serial — snapshots em tempo real
# ═══════════════════════════════════════════════════════════════════════

def print_snapshot_hall(snapshot: dict) -> None:
    freq = snapshot.get("frequency_hz", "-")
    duty = snapshot.get("duty_permille", 0)
    rpm = snapshot.get("rpm_inferred", "-")
    _console.print(
        f"  [cyan]◆ Hall[/]  freq={freq}Hz  "
        f"duty={duty/10:.1f}%  "
        f"rpm={rpm}",
        highlight=False,
    )


def print_snapshot_power(snapshot: dict) -> None:
    tensao = snapshot.get("bus_voltage_mv", 0) / 1000
    corrente = snapshot.get("current_ma", "-")
    potencia = snapshot.get("power_mw", "-")
    _console.print(
        f"  [green]◆ Power[/] bus={tensao:.2f}V  "
        f"current={corrente}mA  "
        f"power={potencia}mW",
        highlight=False,
    )


def print_snapshot_vibration(snapshot: dict) -> None:
    rms = snapshot.get("rms_norm_mg", "-")
    pico = snapshot.get("peak_norm_mg", "-")
    qual = snapshot.get("quality_permille", 0)
    _console.print(
        f"  [magenta]◆ Vib[/] rms={rms}mg  "
        f"peak={pico}mg  "
        f"qual={qual/10:.1f}%",
        highlight=False,
    )


def print_snapshot_course(snapshot: dict) -> None:
    curso = snapshot.get("course_mm", "-")
    disp = snapshot.get("displacement_mm", "-")
    qual = snapshot.get("quality_permille", 0)
    _console.print(
        f"  [yellow]◆ Curso[/] curso={curso}mm  "
        f"disp={disp}mm  "
        f"qual={qual/10:.1f}%",
        highlight=False,
    )


def print_snapshot_capturado(snapshot: dict) -> None:
    tipo = snapshot.get("type", "")
    if tipo == "hall_snapshot":
        print_snapshot_hall(snapshot)
    elif tipo == "power_snapshot":
        print_snapshot_power(snapshot)
    elif tipo == "vibration_snapshot":
        print_snapshot_vibration(snapshot)
    elif tipo == "course_snapshot":
        print_snapshot_course(snapshot)


def print_inicio_captura(config: Any) -> None:
    _console.print()
    _console.print(Panel(
        f"[bold green]Iniciando captura[/]\n\n"
        f"Porta: [cyan]{config.porta_serial}[/] @ {config.baudrate} baud  "
        f"Duração: [cyan]{config.duracao_seg}s[/]\n"
        f"Máquina: [yellow]{config.fabricante} {config.modelo}[/]  "
        f"Série: [yellow]{config.numero_serie}[/]\n"
        f"Tipo: [yellow]{config.tipo_coleta}[/]"
        + (f"  Peça: [yellow]{config.peca_substituida}[/]" if getattr(config, 'peca_substituida', '') else ""),
        border_style="green",
        box=box.ROUNDED,
        title="🔬 Captura Serial",
        title_align="left",
    ))
    _console.print()
    _console.print("[dim]Aguardando dados TMA_DATA... Ctrl-C para interromper[/]")
    _console.print()


def print_fim_captura(total: int, duracao: float) -> None:
    _console.print()
    rate = total / duracao if duracao > 0 else 0
    _console.print(Panel(
        f"[bold]Captura concluída[/]\n\n"
        f"Snapshots: [cyan]{total}[/] em [cyan]{duracao:.1f}s[/]  "
        f"([cyan]{rate:.0f}[/] snapshots/s)",
        border_style="blue",
        box=box.ROUNDED,
        title="📊 Resultado",
        title_align="left",
    ))
    _console.print()


def print_diagnostico_completo(diagnostico: dict) -> None:
    status = f"{ICON_OK} APROVADO" if diagnostico.get("aprovado") else f"{ICON_FAIL} REPROVADO"
    border = "green" if diagnostico.get("aprovado") else "red"

    _console.print()
    _console.print(Panel(
        Text(status, style=f"bold {border}"),
        border_style=border,
        box=box.ROUNDED,
        title="Diagnóstico",
        title_align="left",
    ))
    diagnosticos = diagnostico.get("diagnosticos_por_vertical", {})
    if diagnosticos:
        for tipo, diags in diagnosticos.items():
            if diags:
                _console.print(Text(f"  {tipo}:", style="bold"))
                for d in diags:
                    _console.print(Text(f"    {d}", style="dim"))
    _console.print()


def print_laudo_salvo(caminho: str) -> None:
    _console.print()
    _console.print(Panel(
        Text(f"Laudo salvo em: {caminho}", style=THEME_SUCCESS),
        border_style="green",
        box=box.MINIMAL,
        title=f"{ICON_OK} Laudo",
        title_align="left",
    ))
    _console.print()


# ═══════════════════════════════════════════════════════════════════════
# Barra de status compacta (para uso durante o loop)
# ═══════════════════════════════════════════════════════════════════════

def print_status_bar(
    agent_id: str,
    session_id: str,
    memory_pct: float = 0.0,
    trace_id: Optional[str] = None,
    backend_ok: bool = True,
) -> None:
    """Barra de status horizontal compacta."""
    bar_color = "green" if memory_pct < 50 else "yellow" if memory_pct < 80 else "red"
    mem_bar = f"[{bar_color}]{'█' * int(memory_pct/10)}{'░' * (10-int(memory_pct/10))}[/]"

    items = [
        f"[cyan]{agent_id}[/]",
        f"[dim]{session_id}[/]",
        f"mem {mem_bar} [bold {bar_color}]{memory_pct:.0f}%[/]",
    ]
    if backend_ok:
        items.append(f"{ICON_OK}")
    if trace_id:
        items.append(f"[dim]{trace_id}[/]")

    _console.print(Rule(
        "  ".join(items),
        style="dim",
        characters=" ",
    ))

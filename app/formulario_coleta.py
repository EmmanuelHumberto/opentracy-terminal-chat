"""Formulario interativo para configuracao da sessao de coleta.

Exibe perguntas no terminal e preenche um SessaoConfig.
"""

from __future__ import annotations

from typing import Optional

from app.captura_serial import SessaoConfig
from app.renderer import _console


def _perguntar(mensagem: str, default: str = "", opcoes: Optional[list[str]] = None) -> str:
    """Faz uma pergunta ao usuario e retorna a resposta."""
    if opcoes:
        opcoes_str = " (" + "/".join(opcoes) + ")"
    else:
        opcoes_str = ""

    if default:
        prompt = f"{mensagem}{opcoes_str} [{default}]: "
    else:
        prompt = f"{mensagem}{opcoes_str}: "

    _console.print()
    _console.print(f"[bold cyan]{prompt}[/]", end="")
    resposta = input().strip()

    if not resposta and default:
        return default

    if opcoes and resposta and resposta not in opcoes:
        _console.print(f"[red]Opcao invalida. Escolha entre: {', '.join(opcoes)}[/]")
        return _perguntar(mensagem, default, opcoes)

    return resposta


def _perguntar_sim_nao(mensagem: str, default: bool = True) -> bool:
    """Pergunta sim/nao."""
    default_str = "sim" if default else "nao"
    resposta = _perguntar(mensagem, default_str, ["sim", "nao"])
    return resposta.lower() in ("sim", "s", "yes", "y")


def preencher_configuracao(porta_padrao: str = "/dev/ttyACM0") -> SessaoConfig:
    """Formulario interativo para preencher a configuracao da sessao.

    Exemplo de uso no chat:
        config = preencher_configuracao()
        # inicia captura com config
    """
    _console.print()
    _console.print("[bold cyan]╔════════════════════════════════════════════════╗[/]")
    _console.print("[bold cyan]║       Configuracao da Sessao de Medicao      ║[/]")
    _console.print("[bold cyan]╚════════════════════════════════════════════════╝[/]")
    _console.print()
    _console.print("[yellow]Preencha os dados da maquina e da coleta:[/]")
    _console.print()

    config = SessaoConfig()

    # --- Dados da maquina ---
    _console.print("[bold]Dados da Maquina:[/]")
    config.fabricante = _perguntar("  Fabricante", "FK Irons")
    config.modelo = _perguntar("  Modelo")
    config.numero_serie = _perguntar("  Nº de Serie")

    # --- Tipo de coleta ---
    _console.print()
    _console.print("[bold]Tipo de Coleta:[/]")
    tipos = ["desempenho", "reparo", "pos-reparo", "homologacao", "bancada"]
    config.tipo_coleta = _perguntar("  Tipo", "desempenho", tipos)

    # --- Se for reparo, peca substituida ---
    if config.tipo_coleta in ("reparo", "pos-reparo"):
        config.peca_substituida = _perguntar("  Peca substituida")
        if not config.peca_substituida and config.tipo_coleta == "reparo":
            _console.print("[yellow]  Aviso: nenhuma peca informada para coleta de reparo.[/]")

    # --- Porta serial ---
    _console.print()
    _console.print("[bold]Conexao:[/]")
    config.porta_serial = _perguntar("  Porta serial", porta_padrao)
    config.baudrate = int(_perguntar("  Baudrate", "115200"))

    # --- Duracao ---
    config.duracao_seg = float(_perguntar("  Duracao (segundos)", "30"))

    # --- Tecnico ---
    config.tecnico = _perguntar("  Tecnico responsavel")

    # --- Observacoes ---
    _console.print()
    _console.print("[bold]Observacoes (opcional):[/]")
    config.observacoes = _perguntar("  Obs")

    # --- Resumo antes de iniciar ---
    _console.print()
    _console.print("[bold cyan]╔════════════════════════════════════════════════╗[/]")
    _console.print("[bold cyan]║              Resumo da Configuracao          ║[/]")
    _console.print("[bold cyan]╚════════════════════════════════════════════════╝[/]")
    _console.print()
    _console.print(f"  Fabricante:    [green]{config.fabricante or 'N/A'}[/]")
    _console.print(f"  Modelo:        [green]{config.modelo or 'N/A'}[/]")
    _console.print(f"  Serie:         [green]{config.numero_serie or 'N/A'}[/]")
    _console.print(f"  Tipo:          [green]{config.tipo_coleta}[/]")
    _console.print(f"  Peca subst.:   [green]{config.peca_substituida or 'N/A'}[/]")
    _console.print(f"  Porta:         [green]{config.porta_serial}[/]")
    _console.print(f"  Baudrate:      [green]{config.baudrate}[/]")
    _console.print(f"  Duracao:       [green]{config.duracao_seg}s[/]")
    _console.print(f"  Tecnico:       [green]{config.tecnico or 'N/A'}[/]")
    _console.print(f"  Obs:           [green]{config.observacoes or 'N/A'}[/]")
    _console.print()

    if not _perguntar_sim_nao("  Iniciar captura?", True):
        _console.print("[yellow]Captura cancelada pelo usuario.[/]")
        raise KeyboardInterrupt("Captura cancelada pelo usuario")

    return config

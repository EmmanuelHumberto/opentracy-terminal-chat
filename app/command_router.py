"""Roteador de comandos de interface (comandos que comecam com /).

Cada comando e uma funcao que recebe o contexto de execucao
e retorna True se o loop deve continuar, False para sair.
"""

from __future__ import annotations

from typing import Any, Callable, Optional


# Tipo: funcao de comando recebe args e contexto, retorna continuar?
CommandFunc = Callable[..., bool]


class CommandRouter:
    """Mapeia comandos `/nome` para funcoes."""

    def __init__(self) -> None:
        self._commands: dict[str, tuple[CommandFunc, str]] = {}

    def register(
        self,
        name: str,
        func: CommandFunc,
        description: str = "",
    ) -> None:
        self._commands[name] = (func, description)

    def dispatch(self, text: str, **context: Any) -> bool:
        """Tenta executar um comando. Retorna True se o comando foi
        reconhecido e executado, False se o texto nao e um comando."""
        if not text.startswith("/"):
            return False

        parts = text[1:].strip().split(maxsplit=1)
        cmd_name = parts[0].lower()
        cmd_args = parts[1] if len(parts) > 1 else ""

        entry = self._commands.get(cmd_name)
        if entry is None:
            return False

        func, _ = entry
        return func(args=cmd_args, **context)

    def list_commands(self) -> list[tuple[str, str]]:
        """Retorna lista de (nome, descricao)."""
        return [(f"/{name}", desc) for name, (_, desc) in sorted(self._commands.items())]

    def is_command(self, text: str) -> bool:
        """Verifica se o texto parece um comando."""
        return text.startswith("/")

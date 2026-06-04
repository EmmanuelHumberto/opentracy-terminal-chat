"""Bootstrap de validacao pre-chat (Fase 1).

Na Fase 1, nao cria nem altera agente. Apenas valida que:
- Backend e runtime estao respondendo
- Agente configurado existe
- Token de API esta presente
"""

from __future__ import annotations

from typing import Optional

from app.auth import AuthError, load_token, token_status
from app.config import Config
from app.opentracy_client import OpenTracyClient, OpenTracyError


class BootstrapResult:
    """Resultado da validacao pre-chat."""

    def __init__(
        self,
        success: bool,
        auth_token: str = "",
        error: Optional[str] = None,
    ) -> None:
        self.success = success
        self.auth_token = auth_token
        self.error = error


def validate(config: Config) -> BootstrapResult:
    """Valida ambiente antes de iniciar o chat.

    Retorna BootstrapResult com token se tudo ok, ou erro.
    """
    client = OpenTracyClient(
        backend_url=config.opentracy.backend_url,
        runtime_url=config.opentracy.runtime_url,
        agent_id=config.opentracy.agent_id,
        timeout=config.opentracy.timeout,
    )

    # --- Token ---
    try:
        auth_token = load_token(config.auth.api_token_file)
    except AuthError as exc:
        return BootstrapResult(
            success=False,
            error=str(exc),
        )

    # --- Backend health ---
    if not client.check_backend_health():
        return BootstrapResult(
            success=False,
            error=(
                f"Backend {config.opentracy.backend_url} nao respondeu. "
                f"Execute 'make up' no OpenTracy."
            ),
        )

    # --- Runtime health ---
    if not client.check_runtime_health():
        return BootstrapResult(
            success=False,
            error=(
                f"Runtime {config.opentracy.runtime_url} nao respondeu. "
                f"Execute 'make up' no OpenTracy."
            ),
        )

    # --- Agente ---
    try:
        agents = client.list_agents(auth_token)
    except OpenTracyError as exc:
        return BootstrapResult(
            success=False,
            error=f"Erro ao listar agentes: {exc}",
        )

    agent_exists = any(
        a.get("id") == config.opentracy.agent_id
        for a in agents
    )
    if not agent_exists:
        return BootstrapResult(
            success=False,
            error=(
                f"Agente '{config.opentracy.agent_id}' nao encontrado no OpenTracy.\n"
                f"Crie o agente manualmente ou execute o bootstrap automatico (Fase 2)."
            ),
        )

    return BootstrapResult(success=True, auth_token=auth_token)

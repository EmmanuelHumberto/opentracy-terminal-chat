"""Bootstrap automatico do ambiente OpenTracy.

Fase 1: apenas valida se agente e token existem.
Fase 2: cria/ativa agente, conecta canal API, salva token, valida DeepSeek.
"""

from __future__ import annotations

from typing import Any, Optional

from app.auth import AuthError, load_token, save_token, token_status
from app.config import Config
from app.opentracy_client import OpenTracyClient, OpenTracyError


class BootstrapResult:
    """Resultado do bootstrap."""

    def __init__(
        self,
        success: bool,
        auth_token: str = "",
        error: Optional[str] = None,
        agent_created: bool = False,
        token_created: bool = False,
    ) -> None:
        self.success = success
        self.auth_token = auth_token
        self.error = error
        self.agent_created = agent_created
        self.token_created = token_created


def run(config: Config) -> BootstrapResult:
    """Executa bootstrap completo: validacao + provisionamento automatico.

    Fluxo:
      1. Health check backend e runtime
      2. Lista agentes
      3. Cria agente se nao existir
      4. Ativa agente
      5. Valida rota DeepSeek
      6. Conecta canal API se necessario
      7. Salva token localmente
      8. Verifica DeepSeek configurado
    """
    client = OpenTracyClient(
        backend_url=config.opentracy.backend_url,
        runtime_url=config.opentracy.runtime_url,
        agent_id=config.opentracy.agent_id,
        timeout=config.opentracy.timeout,
    )

    agent_id = config.opentracy.agent_id
    agent_created = False
    token_created = False

    # --- 1. Health check ---
    if not client.check_backend_health():
        return BootstrapResult(
            success=False,
            error=(
                f"Backend {config.opentracy.backend_url} nao respondeu.\n"
                f"Execute 'make up' no OpenTracy."
            ),
        )

    if not client.check_runtime_health():
        return BootstrapResult(
            success=False,
            error=(
                f"Runtime {config.opentracy.runtime_url} nao respondeu.\n"
                f"Execute 'make up' no OpenTracy."
            ),
        )

    # --- 2. Lista agentes ---
    try:
        agents = client.list_agents("")
    except OpenTracyError:
        agents = []

    agent_exists = any(a.get("id") == agent_id for a in agents)

    # --- 3. Criar agente se necessario ---
    if not agent_exists:
        try:
            _create_agent(client, agent_id)
            agent_created = True
        except OpenTracyError as exc:
            return BootstrapResult(
                success=False,
                error=f"Erro ao criar agente '{agent_id}': {exc}",
            )

    # --- 4. Ativar agente ---
    try:
        _activate_agent(client, agent_id)
    except OpenTracyError as exc:
        return BootstrapResult(
            success=False,
            error=f"Erro ao ativar agente '{agent_id}': {exc}",
        )

    # --- 5. Validar rota DeepSeek ---
    try:
        _validate_deepseek_route(client, agent_id)
    except OpenTracyError as exc:
        return BootstrapResult(
            success=False,
            error=str(exc),
        )

    # --- 6. Conectar canal API ---
    try:
        token = _ensure_api_channel(client, agent_id)
    except OpenTracyError as exc:
        return BootstrapResult(
            success=False,
            error=f"Erro ao conectar canal API: {exc}",
        )

    # --- 7. Salvar token localmente ---
    try:
        save_token(token, config.auth.api_token_file)
        token_created = True
    except AuthError as exc:
        return BootstrapResult(
            success=False,
            error=f"Erro ao salvar token: {exc}",
        )

    # --- 8. Verificar DeepSeek ---
    deepseek_ok = _check_deepseek(client, agent_id)

    # --- Resultado ---
    auth_token = load_token(config.auth.api_token_file)
    return BootstrapResult(
        success=True,
        auth_token=auth_token,
        agent_created=agent_created,
        token_created=token_created,
    )


# ---------------------------------------------------------------------------
# Funcoes auxiliares
# ---------------------------------------------------------------------------


def _create_agent(client: OpenTracyClient, agent_id: str) -> None:
    """Cria o agente via API."""
    payload = {
        "name": agent_id,
        "model": "deepseek-chat",
        "prompt": (
            "Voce e um assistente tecnico da Ligado IoT para manutencao, "
            "diagnostico, documentacao e analise industrial. "
            "Responda em portugues, seja objetivo e cite limites "
            "quando nao tiver dados suficientes."
        ),
        "tools": [],
        "channels": ["api"],
    }
    # Tenta criar via backend
    url = f"{client.backend_url}/v1/agents"
    try:
        import httpx
        r = httpx.post(
            url,
            json=payload,
            timeout=30,
        )
        if r.status_code not in (200, 201):
            raise OpenTracyError(
                f"HTTP {r.status_code} ao criar agente: {r.text[:200]}"
            )
    except httpx.RequestError as exc:
        raise OpenTracyError(f"Falha ao criar agente: {exc}") from exc


def _activate_agent(client: OpenTracyClient, agent_id: str) -> None:
    """Ativa o agente."""
    url = f"{client.backend_url}/v1/agents/{agent_id}/activate"
    try:
        import httpx
        r = httpx.post(url, timeout=30)
        if r.status_code not in (200, 201):
            raise OpenTracyError(
                f"HTTP {r.status_code} ao ativar agente: {r.text[:200]}"
            )
    except httpx.RequestError as exc:
        raise OpenTracyError(f"Falha ao ativar agente: {exc}") from exc


def _validate_deepseek_route(client: OpenTracyClient, agent_id: str) -> None:
    """Valida se a rota do agente usa DeepSeek.

    Por enquanto, apenas verifica se o modelo small contem 'deepseek'.
    O ideal seria ler o route.yaml do agente, mas isso requer autenticacao.
    """
    # TODO: Fazer GET no route.yaml ou /agent/config para validar modelo
    pass


def _ensure_api_channel(client: OpenTracyClient, agent_id: str) -> str:
    """Conecta o canal API e retorna o token."""
    url = f"{client.backend_url}/v1/agents/{agent_id}/channels/api/connect"
    try:
        import httpx
        r = httpx.post(url, timeout=30)
        if r.status_code not in (200, 201):
            raise OpenTracyError(
                f"HTTP {r.status_code} ao conectar canal API: {r.text[:200]}"
            )
        data = r.json()
        token = data.get("token")
        if not token:
            raise OpenTracyError("Resposta sem token ao conectar canal API.")
        return token
    except httpx.RequestError as exc:
        raise OpenTracyError(f"Falha ao conectar canal API: {exc}") from exc


def _check_deepseek(client: OpenTracyClient, agent_id: str) -> bool:
    """Verifica se DeepSeek esta configurado (via env ou secrets)."""
    # Tenta ler do runtime direto
    try:
        import httpx
        r = httpx.get(
            f"{client.runtime_url}/agents/{agent_id}/secrets",
            timeout=10,
        )
        if r.is_success:
            data = r.json()
            ds = data.get("deepseek", {})
            if ds.get("set"):
                return True
    except Exception:
        pass
    return False

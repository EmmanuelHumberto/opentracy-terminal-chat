"""Bootstrap automatico do ambiente OpenTracy.

Fase 1: apenas valida se agente e token existem.
Fase 2: cria/ativa agente, conecta canal API, salva token, valida DeepSeek,
        ajusta rota para DeepSeek se necessario.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from app.auth import AuthError, load_token, save_token
from app.config import Config
from app.opentracy_client import OpenTracyClient, OpenTracyError


# Caminho base do OpenTracy
OPENTRACY_ROOT = "/home/hiatus/Projetos/ligadotattoo/OpenTracy"


class BootstrapResult:
    """Resultado do bootstrap."""

    def __init__(
        self,
        success: bool,
        auth_token: str = "",
        error: Optional[str] = None,
        agent_created: bool = False,
        token_created: bool = False,
        route_updated: bool = False,
    ) -> None:
        self.success = success
        self.auth_token = auth_token
        self.error = error
        self.agent_created = agent_created
        self.token_created = token_created
        self.route_updated = route_updated


def run(config: Config) -> BootstrapResult:
    """Executa bootstrap completo."""
    client = OpenTracyClient(
        backend_url=config.opentracy.backend_url,
        runtime_url=config.opentracy.runtime_url,
        agent_id=config.opentracy.agent_id,
        timeout=config.opentracy.timeout,
    )

    agent_id = config.opentracy.agent_id
    agent_created = False
    token_created = False
    route_updated = False

    # --- 1. Health check ---
    if not client.check_backend_health():
        return BootstrapResult(
            success=False,
            error=f"Backend {config.opentracy.backend_url} nao respondeu.\nExecute 'make up' no OpenTracy.",
        )
    if not client.check_runtime_health():
        return BootstrapResult(
            success=False,
            error=f"Runtime {config.opentracy.runtime_url} nao respondeu.\nExecute 'make up' no OpenTracy.",
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
            return BootstrapResult(success=False, error=f"Erro ao criar agente '{agent_id}': {exc}")

    # --- 4. Ativar agente via API ---
    try:
        _activate_agent(client, agent_id)
    except OpenTracyError as exc:
        return BootstrapResult(success=False, error=f"Erro ao ativar agente '{agent_id}': {exc}")

    # --- 5. Ajustar rota para DeepSeek (tanto em agents/<id>/ quanto em agent/) ---
    try:
        route_updated = _ensure_deepseek_route(agent_id, config)
    except Exception as exc:
        return BootstrapResult(success=False, error=f"Erro ao ajustar rota DeepSeek: {exc}")

    # --- 6. Conectar ou rotacionar canal API ---
    try:
        token = _ensure_api_channel(client, agent_id)
    except OpenTracyError as exc:
        return BootstrapResult(success=False, error=f"Erro ao conectar canal API: {exc}")

    # --- 7. Salvar token localmente ---
    try:
        save_token(token, config.auth.api_token_file)
        token_created = True
    except AuthError as exc:
        return BootstrapResult(success=False, error=f"Erro ao salvar token: {exc}")

    # --- 8. Verificar DeepSeek ---
    deepseek_ok = _check_deepseek(client, agent_id)
    if not deepseek_ok:
        return BootstrapResult(
            success=False,
            error="DeepSeek nao configurado. Adicione DEEPSEEK_API_KEY no .env do OpenTracy.",
        )

    auth_token = load_token(config.auth.api_token_file)
    return BootstrapResult(
        success=True,
        auth_token=auth_token,
        agent_created=agent_created,
        token_created=token_created,
        route_updated=route_updated,
    )


# ---------------------------------------------------------------------------
# Funcoes auxiliares
# ---------------------------------------------------------------------------


def _create_agent(client: OpenTracyClient, agent_id: str) -> None:
    import httpx
    payload = {
        "name": agent_id,
        "model": "deepseek-chat",
        "prompt": "Voce e um assistente tecnico da Ligado IoT para manutencao, diagnostico, documentacao e analise industrial. Responda em portugues, seja objetivo e cite limites quando nao tiver dados suficientes.",
        "tools": [],
        "channels": ["api"],
    }
    try:
        r = httpx.post(f"{client.backend_url}/v1/agents", json=payload, timeout=30)
        if r.status_code not in (200, 201):
            raise OpenTracyError(f"HTTP {r.status_code} ao criar agente: {r.text[:200]}")
    except httpx.RequestError as exc:
        raise OpenTracyError(f"Falha ao criar agente: {exc}") from exc


def _activate_agent(client: OpenTracyClient, agent_id: str) -> None:
    import httpx
    try:
        r = httpx.post(f"{client.backend_url}/v1/agents/{agent_id}/activate", timeout=30)
        if r.status_code not in (200, 201):
            raise OpenTracyError(f"HTTP {r.status_code} ao ativar agente: {r.text[:200]}")
    except httpx.RequestError as exc:
        raise OpenTracyError(f"Falha ao ativar agente: {exc}") from exc


def _ensure_deepseek_route(agent_id: str, config: Config) -> bool:
    """Ajusta a rota para DeepSeek nos dois diretorios: agents/<id>/ e agent/."""
    small = config.model.small
    big = config.model.big
    updated = False

    # Diretorios onde o route.yaml pode estar
    candidates = [
        os.path.join(OPENTRACY_ROOT, "agents", agent_id, "pipeline", "route.yaml"),
        os.path.join(OPENTRACY_ROOT, "agent", "pipeline", "route.yaml"),
    ]

    for route_path in candidates:
        if not os.path.exists(route_path):
            continue

        try:
            with open(route_path) as f:
                content = f.read()

            if "deepseek" in content:
                continue  # ja atualizado

            # Substitui modelos Claude por DeepSeek
            content = content.replace("claude-opus-4-7", small)
            content = content.replace("claude-sonnet-4-6", big)
            content = content.replace("claude-haiku-4-5", small)

            with open(route_path, 'w') as f:
                f.write(content)

            updated = True
        except Exception:
            pass

    return updated


def _ensure_api_channel(client: OpenTracyClient, agent_id: str) -> str:
    import httpx
    try:
        r = httpx.post(f"{client.backend_url}/v1/agents/{agent_id}/channels/api/connect", timeout=30)
        if r.status_code in (200, 201):
            data = r.json()
            token = data.get("token")
            if token:
                return token
    except httpx.RequestError as exc:
        raise OpenTracyError(f"Falha ao conectar canal API: {exc}") from exc

    if r.status_code == 409:
        try:
            r = httpx.post(f"{client.backend_url}/v1/agents/{agent_id}/channels/api/rotate", timeout=30)
            if r.status_code in (200, 201):
                data = r.json()
                token = data.get("token")
                if token:
                    return token
        except httpx.RequestError as exc:
            raise OpenTracyError(f"Falha ao rotacionar token: {exc}") from exc

    raise OpenTracyError(f"HTTP {r.status_code} ao configurar canal API: {r.text[:200]}")


def _check_deepseek(client: OpenTracyClient, agent_id: str) -> bool:
    import httpx
    try:
        r = httpx.get(f"{client.runtime_url}/agents/{agent_id}/secrets", timeout=10)
        if r.is_success:
            data = r.json()
            ds = data.get("deepseek", {})
            if ds.get("set"):
                return True
    except Exception:
        pass
    # Fallback: .env
    env_path = os.path.join(OPENTRACY_ROOT, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path) as f:
                for line in f:
                    if line.startswith("DEEPSEEK_API_KEY") and "=" in line:
                        return True
        except Exception:
            pass
    return False

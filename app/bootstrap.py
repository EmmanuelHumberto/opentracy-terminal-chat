"""Bootstrap automatico do ambiente OpenTracy.

Fase 1: apenas valida se agente e token existem.
Fase 2: cria/ativa agente, conecta canal API, salva token, valida DeepSeek,
        ajusta rota para DeepSeek se necessario.
Fase 3: registra MCP servers (filesystem, search) no agente.
Fase 5: registra diretorios de escrita para write_file.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from app.auth import AuthError, load_token, save_token
from app.config import Config
from app.opentracy_client import OpenTracyClient, OpenTracyError


OPENTRACY_ROOT = "/home/hiatus/Projetos/ligadotattoo/OpenTracy"
TERMINAL_ROOT = "/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat"


class BootstrapResult:
    def __init__(
        self,
        success: bool,
        auth_token: str = "",
        error: Optional[str] = None,
        agent_created: bool = False,
        token_created: bool = False,
        route_updated: bool = False,
        mcp_registered: bool = False,
    ) -> None:
        self.success = success
        self.auth_token = auth_token
        self.error = error
        self.agent_created = agent_created
        self.token_created = token_created
        self.route_updated = route_updated
        self.mcp_registered = mcp_registered


def run(config: Config) -> BootstrapResult:
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
    mcp_registered = False

    # --- 1. Health check ---
    if not client.check_backend_health():
        return BootstrapResult(success=False, error=f"Backend {config.opentracy.backend_url} nao respondeu.\nExecute 'make up' no OpenTracy.")
    if not client.check_runtime_health():
        return BootstrapResult(success=False, error=f"Runtime {config.opentracy.runtime_url} nao respondeu.\nExecute 'make up' no OpenTracy.")

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

    # --- 4. Ativar agente ---
    try:
        _activate_agent(client, agent_id)
    except OpenTracyError as exc:
        return BootstrapResult(success=False, error=f"Erro ao ativar agente '{agent_id}': {exc}")

    # --- 5. Ajustar rota DeepSeek ---
    try:
        route_updated = _ensure_deepseek_route(agent_id, config)
    except Exception as exc:
        return BootstrapResult(success=False, error=f"Erro ao ajustar rota DeepSeek: {exc}")

    # --- 6. Conectar canal API ---
    try:
        token = _ensure_api_channel(client, agent_id)
    except OpenTracyError as exc:
        return BootstrapResult(success=False, error=f"Erro ao conectar canal API: {exc}")

    # --- 7. Salvar token ---
    try:
        save_token(token, config.auth.api_token_file)
        token_created = True
    except AuthError as exc:
        return BootstrapResult(success=False, error=f"Erro ao salvar token: {exc}")

    # --- 8. Verificar DeepSeek ---
    deepseek_ok = _check_deepseek(client, agent_id)
    if not deepseek_ok:
        return BootstrapResult(success=False, error="DeepSeek nao configurado. Adicione DEEPSEEK_API_KEY no .env do OpenTracy.")

    # --- 9. Registrar MCP servers (Fase 3 + Fase 5) ---
    try:
        mcp_registered = _register_mcp_servers(agent_id, config)
    except Exception as exc:
        return BootstrapResult(success=False, error=f"Erro ao registrar MCP servers: {exc}")

    auth_token = load_token(config.auth.api_token_file)
    return BootstrapResult(
        success=True,
        auth_token=auth_token,
        agent_created=agent_created,
        token_created=token_created,
        route_updated=route_updated,
        mcp_registered=mcp_registered,
    )


# ---------------------------------------------------------------------------
# Agente
# ---------------------------------------------------------------------------


def _create_agent(client: OpenTracyClient, agent_id: str) -> None:
    import httpx
    payload = {
        "name": agent_id,
        "model": "deepseek-chat",
        "prompt": "Voce e um assistente tecnico da Ligado IoT. Responda em portugues, seja objetivo.",
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


# ---------------------------------------------------------------------------
# Rota DeepSeek
# ---------------------------------------------------------------------------


def _ensure_deepseek_route(agent_id: str, config: Config) -> bool:
    small = config.model.small
    big = config.model.big
    updated = False
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
                continue
            content = content.replace("claude-opus-4-7", small)
            content = content.replace("claude-sonnet-4-6", big)
            content = content.replace("claude-haiku-4-5", small)
            with open(route_path, 'w') as f:
                f.write(content)
            updated = True
        except Exception:
            pass
    return updated


# ---------------------------------------------------------------------------
# Canal API
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# DeepSeek check
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# MCP Servers (Fase 3 + Fase 5)
# ---------------------------------------------------------------------------


def _register_mcp_servers(agent_id: str, config: Config) -> bool:
    """Registra os servidores MCP no formato que o runtime espera.

    Inclui diretorios de leitura e escrita (Fase 5).
    """
    import json

    allowed_dirs = ":".join(config.security.allowed_read_dirs)
    allowed_write = ":".join(config.security.allowed_write_dirs) if config.security.allowed_write_dirs else allowed_dirs
    max_file_size = str(config.security.max_file_size)
    max_output = str(config.security.max_tool_output_bytes)

    servers = [
        {
            "name": "ligadoai_fs",
            "transport": "stdio",
            "command": "uv",
            "args": ["run", "python", "-m", "ligadoai_tools.filesystem_server"],
            "env": {
                "LIGADOAI_ALLOWED_READ_DIRS": allowed_dirs,
                "LIGADOAI_ALLOWED_WRITE_DIRS": allowed_write,
                "LIGADOAI_MAX_FILE_SIZE": max_file_size,
                "LIGADOAI_MAX_OUTPUT_BYTES": max_output,
            },
            "enabled": True,
            "description": "Ferramentas de leitura e escrita em arquivos autorizados.",
        },
        {
            "name": "ligadoai_search",
            "transport": "stdio",
            "command": "uv",
            "args": ["run", "python", "-m", "ligadoai_tools.search_server"],
            "env": {
                "LIGADOAI_ALLOWED_READ_DIRS": allowed_dirs,
                "LIGADOAI_MAX_OUTPUT_BYTES": max_output,
                "LIGADOAI_MAX_SEARCH_RESULTS": "50",
            },
            "enabled": True,
            "description": "Ferramentas de busca em arquivos (search_files, grep).",
        },
    ]

    mcp_config = {"servers": servers}
    registered = False

    candidates = [
        os.path.join(OPENTRACY_ROOT, "agents", agent_id, "mcp.json"),
        os.path.join(OPENTRACY_ROOT, "agent", "mcp.json"),
    ]

    for mcp_path in candidates:
        try:
            os.makedirs(os.path.dirname(mcp_path), exist_ok=True)
            with open(mcp_path, 'w') as f:
                json.dump(mcp_config, f, indent=2)
            registered = True
        except Exception:
            pass

    return registered

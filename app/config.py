"""Configuracao do LigadoAI Terminal Chat.

Carrega `config.toml` e expoe valores tipados com defaults seguros.
A secao `[mcp]` contem parametros usados pelo bootstrap (Fase 2)
ao registrar servidores MCP no OpenTracy.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class OpenTracyConfig(BaseModel):
    backend_url: str = "http://localhost:8002"
    runtime_url: str = "http://localhost:8001"
    agent_id: str = "ligadoai-terminal"
    timeout: int = 30

    @field_validator("timeout")
    @classmethod
    def _timeout_positive(cls, v: int) -> int:
        if v < 1:
            return 30
        return v


class AuthConfig(BaseModel):
    api_token_file: str = "~/.ligadoai/api_token"


class ModelConfig(BaseModel):
    provider: str = "deepseek"
    small: str = "deepseek-chat"
    big: str = "deepseek-reasoner"
    temperature: float = 0.3
    max_tokens: int = 2048

    @field_validator("temperature")
    @classmethod
    def _temp_range(cls, v: float) -> float:
        return max(0.0, min(2.0, v))

    @field_validator("max_tokens")
    @classmethod
    def _tokens_positive(cls, v: int) -> int:
        return max(64, v)


class MemoryConfig(BaseModel):
    max_history: int = 10
    max_chars_before_summary: int = 16000
    summary_max_chars: int = 2500
    flatten_history_into_request: bool = True

    @field_validator("max_history")
    @classmethod
    def _history_positive(cls, v: int) -> int:
        return max(1, v)


class SecurityConfig(BaseModel):
    allowed_read_dirs: list[str] = ["~/LigadoAI"]
    allowed_write_dirs: list[str] = []
    max_file_size: int = 10 * 1024 * 1024
    max_tool_output_bytes: int = 65536
    block_secrets: bool = True


class McpConfig(BaseModel):
    tool_timeout_seconds: int = 30
    max_restarts_per_server: int = 3
    restart_backoff_seconds: int = 5
    log_tool_errors: bool = True

    @field_validator("tool_timeout_seconds")
    @classmethod
    def _timeout_positive(cls, v: int) -> int:
        return max(5, v)


class KnowledgeConfig(BaseModel):
    source_dir: str = "knowledge"
    output_dir: str = "knowledge_md"
    chunk_size: int = 512
    overlap: int = 50
    ingest_target: str = "../OpenTracy/corpora/indexed"


class UiConfig(BaseModel):
    theme: str = "dark"
    show_timestamp: bool = True
    show_trace_id: bool = True
    show_cost: bool = False


class PathsConfig(BaseModel):
    """Caminhos absolutos do projeto. Configuraveis via config.toml para portabilidade."""

    opentracy_root: str = "~/OpenTracy"
    terminal_root: str = "."

    @property
    def opentracy_path(self) -> Path:
        return Path(os.path.expanduser(self.opentracy_root)).resolve()

    @property
    def terminal_path(self) -> Path:
        return Path(os.path.expanduser(self.terminal_root)).resolve()


class BancoConfig(BaseModel):
    """Configuracao do banco PostgreSQL."""
    host: str = "localhost"
    port: int = 5432
    database: str = "ligadoai"
    user: str = "ligadoai"
    password: str = "ligadoai"
    min_connections: int = 2
    max_connections: int = 10
    vector_dimension: int = 1536

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


class Config(BaseModel):
    opentracy: OpenTracyConfig = OpenTracyConfig()
    auth: AuthConfig = AuthConfig()
    model: ModelConfig = ModelConfig()
    memory: MemoryConfig = MemoryConfig()
    security: SecurityConfig = SecurityConfig()
    mcp: McpConfig = McpConfig()
    knowledge: KnowledgeConfig = KnowledgeConfig()
    ui: UiConfig = UiConfig()
    paths: PathsConfig = PathsConfig()
    banco: BancoConfig = BancoConfig()

    def resolve_paths(self) -> None:
        """Resolve placeholders {paths.*} em todas as configs que usam caminhos.

        Permite que o config.toml use:
            allowed_read_dirs = ["{paths.terminal_root}/knowledge"]
        Em vez de:
            allowed_read_dirs = ["/home/usuario/..."]
        """
        subs = {
            "paths.opentracy_root": str(self.paths.opentracy_path),
            "paths.terminal_root": str(self.paths.terminal_path),
        }

        def _resolve(val: Any) -> Any:
            if isinstance(val, str):
                for key, resolved in subs.items():
                    placeholder = "{" + key + "}"
                    if placeholder in val:
                        val = val.replace(placeholder, resolved)
                return val
            if isinstance(val, list):
                return [_resolve(item) for item in val]
            return val

        # Resolve security dirs
        self.security.allowed_read_dirs = _resolve(self.security.allowed_read_dirs)
        self.security.allowed_write_dirs = _resolve(self.security.allowed_write_dirs)

        # Resolve knowledge ingest_target
        self.knowledge.ingest_target = _resolve(self.knowledge.ingest_target)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_config(path: Optional[Path] = None) -> Config:
    """Carrega config.toml do disco. Se o arquivo nao existir, retorna
    defaults seguros. Se existir mas estiver malformado, levanta excecao
    com mensagem clara."""
    if path is None:
        path = _find_config()

    if not path or not path.is_file():
        return Config()

    raw = _read_toml(path)
    config = Config(**raw)
    config.resolve_paths()
    return config


def _find_config() -> Optional[Path]:
    """Procura config.toml no diretorio atual e parents."""
    candidates = [
        Path.cwd() / "config.toml",
        Path(__file__).resolve().parent.parent / "config.toml",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _read_toml(path: Path) -> dict[str, Any]:
    """Le TOML usando tomli (stdlib >= 3.11) ou tomllib (3.11+)."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            raise RuntimeError(
                "tomli ou tomllib necessario para ler config.toml. "
                "Python 3.11+ ja inclui tomllib."
            )

    with path.open("rb") as f:
        try:
            return tomllib.load(f)
        except Exception as exc:
            raise ValueError(
                f"Erro ao ler {path}: {exc}"
            ) from exc


def expand_path(path_str: str) -> Path:
    """Expande ~ e variaveis de ambiente no caminho."""
    expanded = os.path.expanduser(os.path.expandvars(path_str))
    return Path(expanded).resolve()

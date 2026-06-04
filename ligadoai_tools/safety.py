"""Seguranca para MCP Tools: validacao de caminhos, bloqueio de
path traversal, symlink escape e arquivos de segredos.

Toda tool deve usar estas funcoes para validar caminhos antes de
qualquer operacao de leitura/escrita.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Schema de erro padronizado (secao 12.3 do documento)
# ---------------------------------------------------------------------------

ERROR_CODES = {
    "path_not_allowed": "Caminho fora da area autorizada.",
    "path_traversal": "Tentativa de path traversal detectada.",
    "symlink_escape": "Symlink aponta para fora da area permitida.",
    "secret_file_blocked": "Arquivo bloqueado por conter segredo.",
    "file_too_large": "Arquivo excede o limite de tamanho.",
    "output_truncated": "Saida excedeu o limite de bytes, retornado parcialmente.",
    "file_not_found": "Arquivo ou diretorio nao encontrado.",
    "permission_denied": "Sem permissao de leitura no sistema.",
    "conversion_partial": "Conversor extraiu parte do documento.",
    "conversion_failed": "Conversor nao conseguiu processar o arquivo.",
}


def error_response(code: str, message: str = "", recoverable: bool = False, detail: str = "") -> dict:
    """Retorna um dict de erro no schema padronizado."""
    if not message:
        message = ERROR_CODES.get(code, "Erro desconhecido.")
    return {
        "error": {
            "code": code,
            "message": message,
            "recoverable": recoverable,
            "detail": detail,
        }
    }


def is_error(result: dict) -> bool:
    """Verifica se o resultado de uma tool contem erro."""
    return "error" in result


# ---------------------------------------------------------------------------
# Arquivos de segredo bloqueados
# ---------------------------------------------------------------------------

SECRET_FILES = {
    ".env", "secrets.env", "secrets.enc.json", "api.json",
    "id_rsa", "id_ed25519", "id_ecdsa", ".netrc",
    "credentials.json", "service-account.json", "key.json",
    ".ligadoai", "api_token",
}

SECRET_EXTENSIONS = {".pem", ".key", ".p12", ".pfx", ".keystore"}

SECRET_PATTERNS = [
    "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
    "AWS_SECRET", "AWS_ACCESS_KEY", "TOKEN", "PASSWORD", "SECRET",
]


def is_secret_file(path: Path) -> bool:
    """Verifica se o arquivo parece conter segredos."""
    name = path.name
    if name in SECRET_FILES:
        return True
    if path.suffix in SECRET_EXTENSIONS:
        return True
    # Verifica se o nome contem padroes de segredo
    for pattern in SECRET_PATTERNS:
        if pattern.lower() in name.lower():
            return True
    return False


# ---------------------------------------------------------------------------
# Validacao de caminhos
# ---------------------------------------------------------------------------


def resolve_and_validate(
    path_str: str,
    allowed_dirs: list[str],
    max_file_size: int = 10 * 1024 * 1024,
) -> tuple[Optional[Path], Optional[dict]]:
    """Resolve o caminho e valida contra as regras de seguranca.

    Retorna (path_resolvido, None) se OK, ou (None, dict_erro) se falhar.
    """
    # Expande ~ e vars
    expanded = os.path.expanduser(os.path.expandvars(path_str))
    path = Path(expanded)

    # Resolve caminho absoluto
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError) as exc:
        return None, error_response(
            "path_not_allowed",
            detail=f"Nao foi possivel resolver o caminho: {exc}",
        )

    # Verifica path traversal
    if not _is_subpath(resolved, allowed_dirs):
        return None, error_response(
            "path_not_allowed",
            detail=f"O caminho {resolved} nao esta em nenhuma pasta autorizada: {allowed_dirs}",
        )

    # Verifica symlink escape
    if path.is_symlink():
        target = path.resolve()
        if not _is_subpath(target, allowed_dirs):
            return None, error_response(
                "symlink_escape",
                detail=f"Symlink {path} aponta para {target}, fora da area permitida.",
            )

    # Verifica se existe
    if not resolved.exists():
        return None, error_response(
            "file_not_found",
            detail=f"Arquivo ou diretorio nao encontrado: {resolved}",
        )

    # Verifica se é arquivo de segredo
    if is_secret_file(resolved):
        return None, error_response(
            "secret_file_blocked",
            detail=f"Arquivo bloqueado por conter segredos: {resolved.name}",
        )

    # Verifica tamanho (apenas para arquivos)
    if resolved.is_file():
        try:
            file_size = resolved.stat().st_size
            if file_size > max_file_size:
                return None, error_response(
                    "file_too_large",
                    detail=f"Arquivo tem {file_size} bytes, limite e {max_file_size} bytes.",
                )
        except OSError as exc:
            return None, error_response(
                "permission_denied",
                detail=f"Erro ao acessar arquivo: {exc}",
            )

    return resolved, None


def _is_subpath(path: Path, allowed_dirs: list[str]) -> bool:
    """Verifica se o path esta dentro de um dos diretorios permitidos."""
    try:
        path_resolved = path.resolve()
    except (OSError, RuntimeError):
        return False

    for allowed in allowed_dirs:
        try:
            allowed_resolved = Path(os.path.expanduser(os.path.expandvars(allowed))).resolve()
            if path_resolved == allowed_resolved or allowed_resolved in path_resolved.parents:
                return True
        except (OSError, RuntimeError):
            continue

    return False


def limit_output(content: str, max_bytes: int = 65536) -> tuple[str, bool]:
    """Limita o tamanho da saida de uma tool.

    Retorna (conteudo_limitado, foi_truncado).
    """
    encoded = content.encode("utf-8")
    if len(encoded) <= max_bytes:
        return content, False
    # Trunca no limite de bytes, mantendo caracteres validos
    truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
    return truncated, True

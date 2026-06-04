"""Gerenciamento do token de API do agente.

O token fica em arquivo separado com permissao 0600,
nunca no config.toml. O caminho padrao e ~/.ligadoai/api_token.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Optional


class AuthError(Exception):
    """Erro relacionado a autenticacao."""


def resolve_token_path(token_file: str) -> Path:
    """Resolve o caminho do arquivo de token, expandindo ~ e vars."""
    expanded = os.path.expanduser(os.path.expandvars(token_file))
    return Path(expanded).resolve()


def load_token(token_file: str) -> str:
    """Le o token do arquivo. Levanta AuthError se nao existir ou estiver
    com permissao insegura (diferente de 0600 em POSIX)."""
    path = resolve_token_path(token_file)

    if not path.is_file():
        raise AuthError(
            f"Token nao encontrado em {path}. "
            f"Conecte o canal API do agente e salve o token neste arquivo."
        )

    _check_permissions(path)

    try:
        token = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise AuthError(f"Erro ao ler token de {path}: {exc}") from exc

    if not token:
        raise AuthError(f"Arquivo de token vazio: {path}")

    return token


def save_token(token: str, token_file: str) -> Path:
    """Salva o token em arquivo com permissao 0600.
    Cria o diretorio se necessario."""
    path = resolve_token_path(token_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        path.write_text(token.strip() + "\n", encoding="utf-8")
        _set_permissions_600(path)
    except OSError as exc:
        raise AuthError(f"Erro ao salvar token em {path}: {exc}") from exc

    return path


def token_status(token_file: str) -> dict:
    """Retorna status do token para exibicao ao usuario."""
    path = resolve_token_path(token_file)

    if not path.is_file():
        return {"present": False, "path": str(path), "error": "arquivo nao encontrado"}

    try:
        perms = oct(path.stat().st_mode & 0o777)
        size = path.stat().st_size
        return {
            "present": True,
            "path": str(path),
            "permissions": perms,
            "size": size,
            "secure": _is_permissions_600(path),
        }
    except OSError as exc:
        return {"present": False, "path": str(path), "error": str(exc)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_permissions(path: Path) -> None:
    """Em POSIX, alerta se o arquivo nao tiver permissao 0600 ou mais
    restritiva. Em Windows, nao valida (permissions model diferente)."""
    if os.name == "nt":
        return
    if not _is_permissions_600(path):
        raise AuthError(
            f"Arquivo de token {path} tem permissao {oct(path.stat().st_mode & 0o777)}. "
            f"Execute: chmod 0600 {path}"
        )


def _is_permissions_600(path: Path) -> bool:
    """Verifica se o arquivo tem permissao 0600 (apenas dono le/escreve)."""
    try:
        mode = path.stat().st_mode & 0o777
        return mode == stat.S_IRUSR | stat.S_IWUSR  # 0o600
    except OSError:
        return False


def _set_permissions_600(path: Path) -> None:
    """Tenta setar permissao 0600. Falha silenciosa em Windows."""
    if os.name == "nt":
        return
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass

"""MCP Server: ferramentas de filesystem read-only + utilidades + escrita controlada.

Implementa o protocolo MCP sobre stdio usando JSON-RPC 2.0.

Tools de escrita (Fase 5):
  - write_file: escreve arquivo com confirmacao e backup
  - create_backup: cria copia de seguranca de um arquivo
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ligadoai_tools.safety import (
    error_response,
    limit_output,
    resolve_and_validate,
)


ALLOWED_READ_DIRS = os.environ.get(
    "LIGADOAI_ALLOWED_READ_DIRS",
    os.path.expanduser("~/LigadoAI"),
).split(":")

ALLOWED_WRITE_DIRS = os.environ.get(
    "LIGADOAI_ALLOWED_WRITE_DIRS",
    os.path.expanduser("~/LigadoAI"),
).split(":")

MAX_FILE_SIZE = int(os.environ.get("LIGADOAI_MAX_FILE_SIZE", str(10 * 1024 * 1024)))
MAX_OUTPUT_BYTES = int(os.environ.get("LIGADOAI_MAX_OUTPUT_BYTES", "65536"))


# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------

def _is_in_write_dirs(path: Path) -> bool:
    """Verifica se o path esta dentro de um diretorio de escrita permitido."""
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError):
        return False
    for allowed in ALLOWED_WRITE_DIRS:
        try:
            allowed_resolved = Path(os.path.expanduser(os.path.expandvars(allowed))).resolve()
            if resolved == allowed_resolved or allowed_resolved in resolved.parents:
                return True
        except (OSError, RuntimeError):
            continue
    return False


def _create_backup(path: Path) -> dict[str, Any]:
    """Cria backup de um arquivo antes de modificar.

    Retorna dict com informacao do backup ou erro.
    """
    if not path.is_file():
        return error_response("file_not_found", detail=f"Arquivo nao encontrado para backup: {path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(f".{timestamp}.bak")

    try:
        content = path.read_bytes()
        backup_path.write_bytes(content)
        try:
            backup_path.chmod(0o600)
        except OSError:
            pass
    except OSError as exc:
        return error_response("permission_denied", detail=f"Erro ao criar backup: {exc}")

    return {
        "success": True,
        "backup_path": str(backup_path),
        "size": len(content),
    }


# ---------------------------------------------------------------------------
# Tools de leitura (Fase 3)
# ---------------------------------------------------------------------------


def tool_read_file(path: str) -> dict[str, Any]:
    resolved, err = resolve_and_validate(path, ALLOWED_READ_DIRS, MAX_FILE_SIZE)
    if err:
        return err
    if not resolved or not resolved.is_file():
        return error_response("file_not_found", detail=f"Arquivo nao encontrado: {path}")
    try:
        content = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = resolved.read_bytes().hex()[:1000]
            content = f"[binario] {len(content)} bytes (hex preview): {content[:200]}..."
        except OSError as exc:
            return error_response("permission_denied", detail=str(exc))
    except OSError as exc:
        return error_response("permission_denied", detail=str(exc))
    truncated, was_truncated = limit_output(content, MAX_OUTPUT_BYTES)
    result: dict[str, Any] = {"content": truncated}
    if was_truncated:
        result["warning"] = "Saida truncada por exceder limite de bytes."
    return result


def tool_list_directory(path: str = ".") -> dict[str, Any]:
    resolved, err = resolve_and_validate(path, ALLOWED_READ_DIRS, MAX_FILE_SIZE)
    if err:
        return err
    if not resolved or not resolved.is_dir():
        return error_response("file_not_found", detail=f"Diretorio nao encontrado: {path}")
    try:
        entries = []
        for entry in sorted(resolved.iterdir()):
            try:
                entry_stat = entry.stat()
                entries.append({
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size": entry_stat.st_size if entry.is_file() else 0,
                    "modified": datetime.fromtimestamp(entry_stat.st_mtime, tz=timezone.utc).isoformat(),
                })
            except OSError:
                entries.append({"name": entry.name, "type": "unknown"})
    except OSError as exc:
        return error_response("permission_denied", detail=str(exc))
    return {"path": str(resolved), "entries": entries, "total": len(entries)}


def tool_file_info(path: str) -> dict[str, Any]:
    resolved, err = resolve_and_validate(path, ALLOWED_READ_DIRS, MAX_FILE_SIZE)
    if err:
        return err
    if not resolved:
        return error_response("file_not_found", detail=f"Arquivo nao encontrado: {path}")
    try:
        st = resolved.stat()
        info = {
            "name": resolved.name,
            "path": str(resolved),
            "type": "dir" if resolved.is_dir() else "file",
            "size": st.st_size,
            "created": datetime.fromtimestamp(st.st_ctime, tz=timezone.utc).isoformat(),
            "modified": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
            "permissions": oct(st.st_mode & 0o777),
            "is_symlink": resolved.is_symlink(),
        }
        if resolved.is_symlink():
            try:
                info["symlink_target"] = str(resolved.readlink())
            except OSError:
                pass
    except OSError as exc:
        return error_response("permission_denied", detail=str(exc))
    return {"info": info}


def tool_get_current_datetime() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    local_now = datetime.now()
    return {
        "datetime": {
            "utc_iso": now.isoformat(),
            "local_iso": local_now.isoformat(),
            "date": local_now.strftime("%Y-%m-%d"),
            "time": local_now.strftime("%H:%M:%S"),
            "day_of_week": local_now.strftime("%A"),
            "day_of_week_pt": ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"][local_now.weekday()],
            "timestamp": int(local_now.timestamp()),
        }
    }


# ---------------------------------------------------------------------------
# Tools de escrita (Fase 5)
# ---------------------------------------------------------------------------


def tool_write_file(path: str, content: str, create_backup: bool = True) -> dict[str, Any]:
    """Escreve conteudo em um arquivo.

    Regras:
      - Só escreve em diretorios permitidos (ALLOWED_WRITE_DIRS)
      - Cria backup automatico se o arquivo ja existir
      - Nao permite escrever em arquivos de segredo
      - Limite de tamanho do conteudo

    Retorna:
      - "action": "created" se o arquivo foi criado, "updated" se foi sobrescrito.
    """
    from ligadoai_tools.safety import is_secret_file

    expanded = os.path.expanduser(os.path.expandvars(path))
    resolved = Path(expanded).resolve()

    # Verifica se esta em diretorio de escrita permitido
    if not _is_in_write_dirs(resolved):
        return error_response(
            "path_not_allowed",
            detail=f"Escrita nao permitida em: {resolved}. Diretorios permitidos: {ALLOWED_WRITE_DIRS}",
        )

    # Verifica se o arquivo existe e nao e um diretorio
    if resolved.is_dir():
        return error_response("path_not_allowed", detail=f"Nao e possivel sobrescrever um diretorio: {path}")

    # --- CAPTURA EXISTENCIA ANTES DA ESCRITA (correcao do bug) ---
    file_existed = resolved.exists()

    # Verifica se e arquivo de segredo (so se ja existir)
    if file_existed and is_secret_file(resolved):
        return error_response("secret_file_blocked", detail=f"Arquivo bloqueado por conter segredos: {resolved.name}")

    # Verifica tamanho do conteudo
    content_bytes = content.encode("utf-8")
    if len(content_bytes) > MAX_FILE_SIZE:
        return error_response(
            "file_too_large",
            detail=f"Conteudo tem {len(content_bytes)} bytes, limite e {MAX_FILE_SIZE} bytes.",
        )

    # Cria backup se arquivo ja existir
    backup_info = None
    if file_existed and create_backup:
        backup_result = _create_backup(resolved)
        if "error" not in backup_result:
            backup_info = backup_result

    # Escreve o arquivo
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        try:
            resolved.chmod(0o600)
        except OSError:
            pass
    except OSError as exc:
        return error_response("permission_denied", detail=f"Erro ao escrever arquivo: {exc}")

    result: dict[str, Any] = {
        "success": True,
        "path": str(resolved),
        "size": len(content_bytes),
        "action": "updated" if file_existed else "created",  # ← corrigido
    }

    if backup_info:
        result["backup"] = backup_info

    return result


def tool_create_backup(path: str) -> dict[str, Any]:
    """Cria uma copia de seguranca de um arquivo."""
    from ligadoai_tools.safety import resolve_and_validate

    resolved, err = resolve_and_validate(path, ALLOWED_READ_DIRS, MAX_FILE_SIZE)
    if err:
        return err
    if not resolved or not resolved.is_file():
        return error_response("file_not_found", detail=f"Arquivo nao encontrado: {path}")

    result = _create_backup(resolved)
    if "error" in result:
        return result

    return {
        "success": True,
        "backup_path": result["backup_path"],
        "original": str(resolved),
        "size": result["size"],
    }


# ---------------------------------------------------------------------------
# Registro de tools
# ---------------------------------------------------------------------------

TOOLS = {
    "read_file": {"description": "Le o conteudo de um arquivo texto.", "handler": tool_read_file,
        "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    "list_directory": {"description": "Lista arquivos e pastas de um diretorio.", "handler": tool_list_directory,
        "inputSchema": {"type": "object", "properties": {"path": {"type": "string", "description": "Diretorio (padrao: .)"}}}},
    "file_info": {"description": "Metadados de um arquivo.", "handler": tool_file_info,
        "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    "get_current_datetime": {"description": "Data e hora atual do sistema.", "handler": tool_get_current_datetime,
        "inputSchema": {"type": "object", "properties": {}}},
    "write_file": {"description": "Escreve conteudo em um arquivo. Cria backup automatico se o arquivo ja existir. So escreve em diretorios autorizados.", "handler": tool_write_file,
        "inputSchema": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Caminho do arquivo"},
            "content": {"type": "string", "description": "Conteudo a escrever"},
            "create_backup": {"type": "boolean", "description": "Criar backup antes de escrever (padrao: true)"}},
            "required": ["path", "content"]}},
    "create_backup": {"description": "Cria copia de seguranca de um arquivo.", "handler": tool_create_backup,
        "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
}


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 handler
# ---------------------------------------------------------------------------


def handle_request(request: dict) -> dict:
    req_id = request.get("id", 0)
    method = request.get("method", "")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ligadoai_fs", "version": "0.2.0"},
            },
        }

    if method == "notifications/initialized":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        tools_list = [
            {"name": name, "description": info["description"], "inputSchema": info["inputSchema"]}
            for name, info in TOOLS.items()
        ]
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools_list}}

    if method == "tools/call":
        params = request.get("params", {})
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        tool = TOOLS.get(name)
        if not tool:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Tool not found: {name}"}}
        try:
            result = tool["handler"](**arguments)
            if "error" in result:
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(result)}]}}
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(result)}]}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": str(e)}}

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle_request(request)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()

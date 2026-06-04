"""MCP Server: ferramentas de filesystem read-only + utilidades.

Implementa o protocolo MCP sobre stdio usando JSON-RPC 2.0.
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

MAX_FILE_SIZE = int(os.environ.get("LIGADOAI_MAX_FILE_SIZE", str(10 * 1024 * 1024)))
MAX_OUTPUT_BYTES = int(os.environ.get("LIGADOAI_MAX_OUTPUT_BYTES", "65536"))


# ---------------------------------------------------------------------------
# Tools
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


TOOLS = {
    "read_file": {"description": "Le o conteudo de um arquivo texto.", "handler": tool_read_file,
        "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    "list_directory": {"description": "Lista arquivos e pastas de um diretorio.", "handler": tool_list_directory,
        "inputSchema": {"type": "object", "properties": {"path": {"type": "string", "description": "Diretorio (padrao: .)"}}}},
    "file_info": {"description": "Metadados de um arquivo.", "handler": tool_file_info,
        "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    "get_current_datetime": {"description": "Data e hora atual do sistema.", "handler": tool_get_current_datetime,
        "inputSchema": {"type": "object", "properties": {}}},
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
                "serverInfo": {"name": "ligadoai_fs", "version": "0.1.0"},
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

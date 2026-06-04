"""MCP Server: ferramentas de busca.

Implementa o protocolo MCP sobre stdio usando JSON-RPC 2.0.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ligadoai_tools.safety import error_response, resolve_and_validate


ALLOWED_READ_DIRS = os.environ.get("LIGADOAI_ALLOWED_READ_DIRS", os.path.expanduser("~/LigadoAI")).split(":")
MAX_OUTPUT_BYTES = int(os.environ.get("LIGADOAI_MAX_OUTPUT_BYTES", "65536"))
MAX_RESULTS = int(os.environ.get("LIGADOAI_MAX_SEARCH_RESULTS", "50"))


def tool_search_files(pattern: str, path: str = ".", max_results: int = 50) -> dict[str, Any]:
    resolved, err = resolve_and_validate(path, ALLOWED_READ_DIRS)
    if err:
        return err
    if not resolved or not resolved.is_dir():
        return error_response("file_not_found", detail=f"Diretorio nao encontrado: {path}")
    try:
        matches = []
        for entry in resolved.rglob(pattern):
            if len(matches) >= max_results:
                break
            try:
                entry_stat = entry.stat()
                matches.append({
                    "name": entry.name,
                    "path": str(entry.relative_to(resolved)),
                    "type": "dir" if entry.is_dir() else "file",
                    "size": entry_stat.st_size if entry.is_file() else 0,
                    "modified": datetime.fromtimestamp(entry_stat.st_mtime, tz=timezone.utc).isoformat(),
                })
            except OSError:
                continue
    except OSError as exc:
        return error_response("permission_denied", detail=str(exc))
    return {"pattern": pattern, "base_path": str(resolved), "matches": matches, "total": len(matches), "truncated": len(matches) >= max_results}


def tool_grep(pattern: str, path: str = ".", max_results: int = 50) -> dict[str, Any]:
    resolved, err = resolve_and_validate(path, ALLOWED_READ_DIRS)
    if err:
        return err
    if not resolved or not resolved.is_dir():
        return error_response("file_not_found", detail=f"Diretorio nao encontrado: {path}")
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        return error_response("invalid_pattern", detail=f"Padrao regex invalido: {exc}")
    try:
        matches = []
        for entry in resolved.rglob("*"):
            if not entry.is_file():
                continue
            if len(matches) >= max_results:
                break
            try:
                if entry.stat().st_size > 1024 * 1024:
                    continue
            except OSError:
                continue
            try:
                content = entry.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for line_no, line in enumerate(content.split("\n"), 1):
                if regex.search(line):
                    matches.append({"file": str(entry.relative_to(resolved)), "line": line_no, "content": line.strip()[:200]})
                    if len(matches) >= max_results:
                        break
    except OSError as exc:
        return error_response("permission_denied", detail=str(exc))
    return {"pattern": pattern, "base_path": str(resolved), "matches": matches, "total": len(matches), "truncated": len(matches) >= max_results}


TOOLS = {
    "search_files": {"description": "Busca arquivos por nome ou padrao glob.", "handler": tool_search_files,
        "inputSchema": {"type": "object", "properties": {
            "pattern": {"type": "string"}, "path": {"type": "string", "description": "Diretorio base"},
            "max_results": {"type": "integer"}}, "required": ["pattern"]}},
    "grep": {"description": "Busca texto dentro de arquivos (regex).", "handler": tool_grep,
        "inputSchema": {"type": "object", "properties": {
            "pattern": {"type": "string"}, "path": {"type": "string", "description": "Diretorio base"},
            "max_results": {"type": "integer"}}, "required": ["pattern"]}},
}


def handle_request(request: dict) -> dict:
    req_id = request.get("id", 0)
    method = request.get("method", "")

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": req_id, "result": {
            "protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
            "serverInfo": {"name": "ligadoai_search", "version": "0.1.0"}}}

    if method == "notifications/initialized":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        tools_list = [{"name": n, "description": i["description"], "inputSchema": i["inputSchema"]} for n, i in TOOLS.items()]
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

"""Logs estruturados em JSONL com rotacao.

Eventos registrados:
  - chat: chamada de chat (request/response, trace_id, latencia)
  - error: erros HTTP, de configuracao, etc.
  - tool_error: erros de MCP tools (code, recoverable)
  - memory_summary: resumo de sessao gerado
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# Rotacao: manter 7 dias de logs
_MAX_LOG_FILES = 7


class JsonlLogger:
    """Logger que escreve eventos em arquivos JSONL diarios.

    Uso:
        logger = JsonlLogger(Path("logs"))
        logger.log("chat", session_id="default", trace_id="...", success=True)
    """

    def __init__(self, log_dir: Path) -> None:
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._rotate_old_logs()

    def log(
        self,
        event: str,
        *,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        **extra: Any,
    ) -> None:
        """Escreve um evento no arquivo de log do dia."""
        record = {
            "time": _now_iso(),
            "event": event,
        }
        if session_id is not None:
            record["session_id"] = session_id
        if trace_id is not None:
            record["trace_id"] = trace_id
        record.update(extra)

        path = self._today_path()
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            logging.getLogger(__name__).warning(
                "falha ao escrever log em %s", path
            )

    def log_chat(
        self,
        *,
        session_id: str,
        trace_id: Optional[str] = None,
        success: bool,
        duration_ms: float,
        input_chars: int = 0,
        output_chars: int = 0,
    ) -> None:
        self.log(
            "chat",
            session_id=session_id,
            trace_id=trace_id,
            success=success,
            duration_ms=round(duration_ms, 1),
            input_chars=input_chars,
            output_chars=output_chars,
        )

    def log_error(
        self,
        kind: str,
        message: str,
        *,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        **extra: Any,
    ) -> None:
        self.log(
            "error",
            session_id=session_id,
            trace_id=trace_id,
            kind=kind,
            message=message,
            **extra,
        )

    def log_tool_error(
        self,
        *,
        tool: str,
        error_code: str,
        recoverable: bool,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> None:
        self.log(
            "tool_error",
            session_id=session_id,
            trace_id=trace_id,
            tool=tool,
            error_code=error_code,
            recoverable=recoverable,
        )

    def log_memory_summary(
        self,
        *,
        session_id: str,
        summary_chars: int,
    ) -> None:
        self.log(
            "memory_summary",
            session_id=session_id,
            summary_chars=summary_chars,
        )

    # ------------------------------------------------------------------
    # Rotacao
    # ------------------------------------------------------------------

    def _today_path(self) -> Path:
        return self.log_dir / f"terminal-{_today_str()}.jsonl"

    def _rotate_old_logs(self) -> None:
        """Remove arquivos de log mais velhos que _MAX_LOG_FILES dias."""
        import time

        now = time.time()
        for f in sorted(self.log_dir.glob("terminal-*.jsonl")):
            try:
                mtime = f.stat().st_mtime
                if now - mtime > _MAX_LOG_FILES * 86400:
                    f.unlink()
            except OSError:
                pass


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

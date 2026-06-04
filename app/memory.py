"""Memoria local: historico JSONL, resumo Markdown, sessoes.

A CLI mantem seu proprio historico porque o OpenTracy ainda nao
usa `context.history` no prompt do LLM (lacuna 4.1 do documento).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Sessao
# ---------------------------------------------------------------------------


class Session:
    """Representa uma sessao de conversa."""

    def __init__(
        self,
        session_id: str,
        conversations_dir: Path,
        memory_dir: Path,
    ) -> None:
        self.session_id = session_id
        self._conv_dir = conversations_dir
        self._mem_dir = memory_dir
        self._conv_dir.mkdir(parents=True, exist_ok=True)
        self._mem_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Historico (JSONL)
    # ------------------------------------------------------------------

    @property
    def history_path(self) -> Path:
        return self._conv_dir / f"{self.session_id}.jsonl"

    def add_message(self, role: str, content: str, trace_id: Optional[str] = None) -> None:
        """Adiciona uma mensagem ao historico."""
        record = {
            "time": _now_iso(),
            "role": role,
            "content": content,
        }
        if trace_id is not None:
            record["trace_id"] = trace_id

        with self.history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def get_recent(self, n: int) -> list[dict[str, Any]]:
        """Retorna as ultimas N mensagens."""
        messages = self._load_all()
        return messages[-n:]

    def get_all(self) -> list[dict[str, Any]]:
        return self._load_all()

    def count_messages_since_summary(self) -> int:
        """Conta mensagens apos o ultimo resumo."""
        messages = self._load_all()
        summary_mtime = self._summary_mtime()
        if summary_mtime is None:
            return len(messages)
        count = 0
        for m in messages:
            t = m.get("time", "")
            if t > summary_mtime:
                count += 1
        return count

    def estimated_context_chars(
        self,
        summary: Optional[str],
        recent: list[dict[str, Any]],
        user_message: str,
    ) -> int:
        """Estima o total de caracteres do contexto."""
        total = 0
        if summary:
            total += len(summary)
        for m in recent:
            total += len(m.get("content", ""))
        total += len(user_message)
        return total

    def trim_history_after_summary(self, keep_last: int = 2) -> None:
        """Remove mensagens antigas do JSONL, mantendo apenas as ultimas
        `keep_last` mensagens apos o ultimo resumo. Isso evita que o
        historico cresca indefinidamente."""
        messages = self._load_all()
        if len(messages) <= keep_last:
            return

        # Mantem apenas as ultimas N mensagens
        trimmed = messages[-keep_last:]

        # Reescreve o arquivo
        with self.history_path.open("w", encoding="utf-8") as f:
            for msg in trimmed:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------
    # Resumo (Markdown)
    # ------------------------------------------------------------------

    @property
    def summary_path(self) -> Path:
        return self._mem_dir / f"{self.session_id}_summary.md"

    def load_summary(self) -> Optional[str]:
        """Carrega o resumo da sessao, se existir."""
        path = self.summary_path
        if not path.is_file():
            return None
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError:
            return None

    def save_summary(self, summary: str) -> None:
        """Salva o resumo da sessao."""
        self.summary_path.write_text(summary.strip() + "\n", encoding="utf-8")

    def _summary_mtime(self) -> Optional[str]:
        """Retorna o timestamp ISO do ultimo resumo, ou None."""
        path = self.summary_path
        if not path.is_file():
            return None
        try:
            mtime = path.stat().st_mtime
            dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
            return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        except OSError:
            return None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load_all(self) -> list[dict[str, Any]]:
        path = self.history_path
        if not path.is_file():
            return []
        messages: list[dict[str, Any]] = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        messages.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return messages


# ---------------------------------------------------------------------------
# Gerenciador de sessoes
# ---------------------------------------------------------------------------


class SessionManager:
    """Gerencia multiplas sessoes de conversa."""

    def __init__(
        self,
        conversations_dir: Path,
        memory_dir: Path,
    ) -> None:
        self._conv_dir = conversations_dir
        self._mem_dir = memory_dir
        self._conv_dir.mkdir(parents=True, exist_ok=True)
        self._mem_dir.mkdir(parents=True, exist_ok=True)
        self._sessions_index = self._conv_dir / "sessions.json"
        self._current_id: str = "default"

    @property
    def current(self) -> Session:
        return Session(self._current_id, self._conv_dir, self._mem_dir)

    @property
    def current_id(self) -> str:
        return self._current_id

    def create_session(self, session_id: Optional[str] = None) -> str:
        """Cria uma nova sessao e torna ativa."""
        if session_id is None:
            session_id = _generate_session_id()
        self._current_id = session_id
        self._touch_session(session_id)
        return session_id

    def list_sessions(self) -> list[dict[str, Any]]:
        """Lista sessoes existentes."""
        index = self._load_index()
        sessions = []
        for sid in index.get("sessions", []):
            session = Session(sid, self._conv_dir, self._mem_dir)
            history = session.get_all()
            sessions.append({
                "id": sid,
                "message_count": len(history),
                "last_message": history[-1]["time"] if history else None,
                "has_summary": session.summary_path.is_file(),
            })
        return sessions

    def load_session(self, session_id: str) -> bool:
        """Carrega uma sessao existente. Retorna False se nao existir."""
        session = Session(session_id, self._conv_dir, self._mem_dir)
        if not session.history_path.is_file():
            return False
        self._current_id = session_id
        return True

    def _touch_session(self, session_id: str) -> None:
        index = self._load_index()
        sessions = index.setdefault("sessions", [])
        if session_id not in sessions:
            sessions.append(session_id)
        self._save_index(index)

    def _load_index(self) -> dict[str, Any]:
        if not self._sessions_index.is_file():
            return {"sessions": []}
        try:
            with self._sessions_index.open(encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"sessions": []}

    def _save_index(self, index: dict[str, Any]) -> None:
        with self._sessions_index.open("w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
            f.write("\n")


# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _generate_session_id() -> str:
    import secrets
    return f"sess_{secrets.token_hex(4)}"

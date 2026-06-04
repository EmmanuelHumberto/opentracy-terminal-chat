"""Testes para app/logger.py"""

import json
import tempfile
from pathlib import Path

from app.logger import JsonlLogger


def test_log_event():
    """Log de evento deve criar arquivo JSONL."""
    with tempfile.TemporaryDirectory() as tmp:
        log_dir = Path(tmp)
        logger = JsonlLogger(log_dir)

        logger.log("chat", session_id="sess_1", success=True, duration_ms=100)

        # Verificar arquivo
        files = list(log_dir.glob("terminal-*.jsonl"))
        assert len(files) == 1

        with files[0].open() as f:
            line = f.readline().strip()
            record = json.loads(line)
            assert record["event"] == "chat"
            assert record["session_id"] == "sess_1"
            assert record["success"] is True


def test_log_chat():
    """Metodo helper log_chat."""
    with tempfile.TemporaryDirectory() as tmp:
        log_dir = Path(tmp)
        logger = JsonlLogger(log_dir)

        logger.log_chat(
            session_id="sess_1",
            trace_id="trace_abc",
            success=True,
            duration_ms=123.4,
            input_chars=500,
            output_chars=300,
        )

        files = list(log_dir.glob("terminal-*.jsonl"))
        with files[0].open() as f:
            record = json.loads(f.readline())
            assert record["event"] == "chat"
            assert record["trace_id"] == "trace_abc"


def test_log_error():
    """Metodo helper log_error."""
    with tempfile.TemporaryDirectory() as tmp:
        log_dir = Path(tmp)
        logger = JsonlLogger(log_dir)

        logger.log_error("http_401", "unauthorized", session_id="sess_1")

        files = list(log_dir.glob("terminal-*.jsonl"))
        with files[0].open() as f:
            record = json.loads(f.readline())
            assert record["event"] == "error"
            assert record["kind"] == "http_401"

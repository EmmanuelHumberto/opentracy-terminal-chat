"""Testes para app/memory.py"""

import tempfile
from pathlib import Path

from app.memory import Session, SessionManager


def test_add_and_get_messages():
    """Adicionar e recuperar mensagens."""
    with tempfile.TemporaryDirectory() as tmp:
        conv = Path(tmp) / "conv"
        mem = Path(tmp) / "mem"
        session = Session("test_sess", conv, mem)

        session.add_message("user", "Ola")
        session.add_message("assistant", "Oi!")

        all_msgs = session.get_all()
        assert len(all_msgs) == 2
        assert all_msgs[0]["role"] == "user"
        assert all_msgs[1]["role"] == "assistant"


def test_get_recent():
    """Recuperar ultimas N mensagens."""
    with tempfile.TemporaryDirectory() as tmp:
        conv = Path(tmp) / "conv"
        mem = Path(tmp) / "mem"
        session = Session("test_recent", conv, mem)

        for i in range(5):
            session.add_message("user", f"msg_{i}")

        recent = session.get_recent(3)
        assert len(recent) == 3
        assert recent[-1]["content"] == "msg_4"


def test_summary():
    """Salvar e carregar resumo."""
    with tempfile.TemporaryDirectory() as tmp:
        conv = Path(tmp) / "conv"
        mem = Path(tmp) / "mem"
        session = Session("test_summary", conv, mem)

        assert session.load_summary() is None

        session.save_summary("Resumo de teste.")
        loaded = session.load_summary()
        assert loaded == "Resumo de teste."


def test_estimated_context_chars():
    """Estimativa de caracteres do contexto."""
    with tempfile.TemporaryDirectory() as tmp:
        conv = Path(tmp) / "conv"
        mem = Path(tmp) / "mem"
        session = Session("test_chars", conv, mem)

        estimated = session.estimated_context_chars(
            summary="Resumo: 10 chars",
            recent=[{"content": "Msg: 10 chars"}, {"content": "Outra: 12 chars"}],
            user_message="User: 9 chars",
        )
        # 10 + 10 + 12 + 9 = 41
        assert estimated == 41


def test_session_manager():
    """Gerenciador de sessoes."""
    with tempfile.TemporaryDirectory() as tmp:
        conv = Path(tmp) / "conv"
        mem = Path(tmp) / "mem"
        mgr = SessionManager(conv, mem)

        assert mgr.current_id == "default"

        # Criar nova sessao
        sid = mgr.create_session()
        assert mgr.current_id == sid

        # Listar
        sessions = mgr.list_sessions()
        assert len(sessions) >= 2  # default + nova

        # Carregar
        assert mgr.load_session("default") is True
        assert mgr.current_id == "default"

        # Carregar inexistente
        assert mgr.load_session("nao_existe") is False

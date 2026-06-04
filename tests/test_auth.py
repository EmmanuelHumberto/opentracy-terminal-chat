"""Testes para app/auth.py"""

import os
import stat
import tempfile
from pathlib import Path

import pytest

from app.auth import (
    AuthError,
    load_token,
    save_token,
    token_status,
    resolve_token_path,
)


def test_save_and_load_token():
    """Salvar e ler token deve funcionar."""
    with tempfile.TemporaryDirectory() as tmp:
        token_file = str(Path(tmp) / "api_token")
        save_token("ot_abc123", token_file)
        loaded = load_token(token_file)
        assert loaded == "ot_abc123"


def test_load_missing_token():
    """Token ausente deve levantar erro."""
    with tempfile.TemporaryDirectory() as tmp:
        token_file = str(Path(tmp) / "missing_token")
        with pytest.raises(AuthError, match="nao encontrado"):
            load_token(token_file)


def test_load_empty_token():
    """Token vazio deve levantar erro."""
    with tempfile.TemporaryDirectory() as tmp:
        token_file = str(Path(tmp) / "empty_token")
        Path(token_file).write_text("  \n")
        with pytest.raises(AuthError, match="vazio"):
            load_token(token_file)


def test_token_status():
    """Status do token deve refletir estado real."""
    with tempfile.TemporaryDirectory() as tmp:
        token_file = str(Path(tmp) / "api_token")

        # Ausente
        status = token_status(token_file)
        assert status["present"] is False

        # Presente
        save_token("ot_abc", token_file)
        status = token_status(token_file)
        assert status["present"] is True
        assert "path" in status


def test_resolve_path():
    """Resolucao de caminho deve expandir ~."""
    path = resolve_token_file("~/test_token")
    assert str(path).startswith("/")
    assert path.name == "test_token"

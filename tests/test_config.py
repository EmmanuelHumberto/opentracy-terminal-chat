"""Testes para app/config.py"""

from pathlib import Path
import tempfile

from app.config import Config, load_config, expand_path


def test_default_config():
    """Sem arquivo, deve retornar defaults seguros."""
    cfg = load_config()
    assert cfg.opentracy.backend_url == "http://localhost:8002"
    assert cfg.opentracy.timeout == 30
    assert cfg.model.provider == "deepseek"
    assert cfg.memory.max_history == 10
    assert cfg.memory.max_chars_before_summary == 16000  # 4000 * 4


def test_custom_config():
    """Arquivo personalizado deve sobrepor defaults."""
    toml_content = """
[opentracy]
backend_url = "http://localhost:9000"
timeout = 60

[model]
temperature = 0.7
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        tmp_path = Path(f.name)

    try:
        cfg = load_config(tmp_path)
        assert cfg.opentracy.backend_url == "http://localhost:9000"
        assert cfg.opentracy.timeout == 60
        assert cfg.model.temperature == 0.7
        # Nao modificado
        assert cfg.model.provider == "deepseek"
    finally:
        tmp_path.unlink()


def test_expand_path():
    """Expansao de ~ deve funcionar."""
    path = expand_path("~/teste")
    assert str(path).startswith("/")
    assert path.name == "teste"


def test_mcp_config_defaults():
    """Secao mcp deve ter defaults."""
    cfg = load_config()
    assert cfg.mcp.tool_timeout_seconds == 30
    assert cfg.mcp.max_restarts_per_server == 3

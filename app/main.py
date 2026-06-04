"""Ponto de entrada do LigadoAI Terminal Chat.

Uso:
    uv run python -m app.main
    uv run python -m app.main --mock   # modo offline para testes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.bootstrap import validate
from app.chat import ChatContext, build_router, run_chat_loop
from app.config import load_config
from app.logger import JsonlLogger
from app.memory import SessionManager
from app.opentracy_client import OpenTracyClient
from app.renderer import print_error, print_info


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LigadoAI Terminal Chat - CLI para OpenTracy"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Modo mock: nao conecta ao OpenTracy",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Caminho alternativo para config.toml",
    )
    args = parser.parse_args()

    # --- Config ---
    config_path = Path(args.config) if args.config else None
    try:
        config = load_config(config_path)
    except Exception as exc:
        print_error(f"Erro ao carregar configuracao: {exc}")
        sys.exit(1)

    # --- Diretorios de dados ---
    base_dir = Path(__file__).resolve().parent.parent
    conv_dir = base_dir / "conversations"
    mem_dir = base_dir / "memory"
    log_dir = base_dir / "logs"

    # --- Logger ---
    logger = JsonlLogger(log_dir)

    # --- Modo mock ---
    if args.mock:
        _run_mock(config, conv_dir, mem_dir, logger)
        return

    # --- Bootstrap ---
    result = validate(config)
    if not result.success:
        print_error(result.error or "Falha na validacao do ambiente.")
        sys.exit(1)

    auth_token = result.auth_token
    print_info("Ambiente validado com sucesso.")

    # --- Cliente HTTP ---
    client = OpenTracyClient(
        backend_url=config.opentracy.backend_url,
        runtime_url=config.opentracy.runtime_url,
        agent_id=config.opentracy.agent_id,
        timeout=config.opentracy.timeout,
    )

    # --- Sessoes ---
    sessions = SessionManager(conv_dir, mem_dir)

    # --- Router ---
    router = build_router()

    # --- Contexto ---
    ctx = ChatContext(
        config=config,
        client=client,
        sessions=sessions,
        logger=logger,
        router=router,
        auth_token=auth_token,
    )

    # --- Loop ---
    try:
        run_chat_loop(ctx)
    except KeyboardInterrupt:
        print_info("\nEncerrando...")
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Modo mock
# ---------------------------------------------------------------------------


def _run_mock(
    config: object,
    conv_dir: Path,
    mem_dir: Path,
    logger: JsonlLogger,
) -> None:
    """Modo offline para testes, sem OpenTracy."""
    from app.chat import ChatContext, build_router, run_chat_loop
    from app.memory import SessionManager

    sessions = SessionManager(conv_dir, mem_dir)
    router = build_router()

    # Cliente mock
    class MockClient:
        def check_backend_health(self) -> bool:
            return True
        def check_runtime_health(self) -> bool:
            return True
        def list_agents(self, auth_token: str) -> list:
            return [{"id": "ligadoai-terminal"}]
        def chat(self, request: str, history=None, *, auth_token="", channel="terminal") -> dict:
            return {
                "response": f"[mock] Recebi: {request[:100]}...",
                "trace_id": "mock_trace_001",
                "duration_ms": 0,
                "success": True,
                "error": None,
            }
        def close(self) -> None:
            pass

    ctx = ChatContext(
        config=config,  # type: ignore
        client=MockClient(),  # type: ignore
        sessions=sessions,
        logger=logger,
        router=router,
        auth_token="mock_token",
    )

    print_info("Modo MOCK - sem conexao com OpenTracy.")
    try:
        run_chat_loop(ctx)
    except KeyboardInterrupt:
        print_info("\nEncerrando...")


if __name__ == "__main__":
    main()

"""Ponto de entrada do LigadoAI Terminal Chat.

Uso:
    uv run python -m app.main
    uv run python -m app.main --mock   # modo offline para testes
    uv run python -m app.main --bootstrap  # forca bootstrap mesmo se token existir
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.bootstrap import run as run_bootstrap
from app.chat import ChatContext, build_router, run_chat_loop
from app.config import load_config
from app.logger import JsonlLogger
from app.memory import SessionManager
from app.opentracy_client import OpenTracyClient
from app.renderer import print_error, print_info, print_success


def _ensure_opentracy_services(config) -> list[object]:
    """Garante que runtime e backend do OpenTracy estejam rodando.

    O chat envia mensagens para o backend (:8002), que repassa para o
    runtime (:8001). Subir apenas o runtime deixa o terminal vivo, mas as
    chamadas de resumo/chat falham com "Connection refused".
    """
    import subprocess
    import time
    import urllib.request
    import urllib.error
    import urllib.parse

    runtime_url = config.opentracy.runtime_url.rstrip("/")
    backend_url = config.opentracy.backend_url.rstrip("/")
    runtime_port = str(urllib.parse.urlparse(runtime_url).port or 8001)
    backend_port = str(urllib.parse.urlparse(backend_url).port or 8002)
    health_urls = {
        "runtime": f"{runtime_url}/health",
        "backend": f"{backend_url}/health",
    }

    def _healthy(service: str, timeout: float = 2) -> bool:
        try:
            req = urllib.request.Request(health_urls[service])
            urllib.request.urlopen(req, timeout=timeout)
            return True
        except (urllib.error.URLError, OSError):
            return False

    def _all_healthy() -> bool:
        return all(_healthy(service) for service in health_urls)

    if _all_healthy():
        print_info("OpenTracy runtime/backend ja estao rodando.")
        return []

    print_info("Iniciando OpenTracy runtime/backend automaticamente...")
    opentracy_root = config.paths.opentracy_path
    run_dir = opentracy_root / ".run"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Remove VIRTUAL_ENV do ambiente para evitar warning do uv
    import os as _os
    env = _os.environ.copy()
    env.pop("VIRTUAL_ENV", None)

    procs: list[object] = []

    if not _healthy("runtime"):
        runtime_log = (run_dir / "runtime.log").open("ab")
        proc = subprocess.Popen(
            ["uv", "run", "python", "-m", "runtime.server"],
            cwd=str(opentracy_root),
            stdout=runtime_log,
            stderr=runtime_log,
            env={**env, "OPENTRACY_RUNTIME_PORT": runtime_port},
        )
        procs.append(proc)

    if not _healthy("backend"):
        backend_log = (run_dir / "backend.log").open("ab")
        proc = subprocess.Popen(
            ["npm", "run", "start"],
            cwd=str(opentracy_root / "backend"),
            stdout=backend_log,
            stderr=backend_log,
            env={
                **env,
                "PORT": backend_port,
                "RUNTIME_URL": runtime_url,
            },
        )
        procs.append(proc)

    # Aguarda os health checks responderem (timeout 30s)
    for _ in range(30):
        time.sleep(1)
        if _all_healthy():
            print_success("OpenTracy runtime/backend iniciados com sucesso.")
            return procs

    print_error("Timeout ao iniciar OpenTracy runtime/backend (30s).")
    return procs


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
        "--bootstrap",
        action="store_true",
        help="Forca bootstrap automatico mesmo se token existir",
    )
    parser.add_argument(
        "--no-runtime",
        action="store_true",
        help="Nao inicia o OpenTracy runtime/backend automaticamente",
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
    if args.bootstrap:
        print_info("Executando bootstrap automatico...")
        result = run_bootstrap(config)
        if not result.success:
            print_error(result.error or "Falha no bootstrap.")
            sys.exit(1)
        if result.agent_created:
            print_success(f"Agente '{config.opentracy.agent_id}' criado.")
        if result.token_created:
            print_success("Token do canal API salvo.")
        print_info("Bootstrap concluido com sucesso.")
    else:
        # Tenta validacao simples primeiro
        from app.auth import load_token as load_token_simple
        try:
            auth_token = load_token_simple(config.auth.api_token_file)
        except Exception:
            # Se nao tem token, faz bootstrap automatico
            print_info("Token nao encontrado. Executando bootstrap automatico...")
            result = run_bootstrap(config)
            if not result.success:
                print_error(result.error or "Falha no bootstrap.")
                sys.exit(1)
            if result.agent_created:
                print_success(f"Agente '{config.opentracy.agent_id}' criado.")
            if result.token_created:
                print_success("Token do canal API salvo.")
            print_info("Bootstrap concluido.")
            auth_token = result.auth_token

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

    # --- Auto-inicializa OpenTracy runtime/backend (a menos que --no-runtime) ---
    opentracy_procs = []
    if not args.no_runtime:
        opentracy_procs = _ensure_opentracy_services(config)

    # --- Loop ---
    try:
        run_chat_loop(ctx)
    except KeyboardInterrupt:
        print_info("\nEncerrando...")
    finally:
        client.close()
        for proc in opentracy_procs:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass


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

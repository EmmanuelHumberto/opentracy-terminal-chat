"""Loop principal do chat."""
from __future__ import annotations
import asyncio, json, time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from app.command_router import CommandRouter
from app.config import Config
from app.logger import JsonlLogger
from app.memory import SessionManager
from app.opentracy_client import OpenTracyClient, OpenTracyError
from app.renderer import (
    print_assistant_message, print_divider, print_error, print_help,
    print_info, print_memory_status, print_session_list, print_status,
    print_success, print_trace_id, print_welcome, clear_screen, prompt_input,
    print_snapshot_capturado, print_inicio_captura, print_fim_captura,
    print_diagnostico_completo, print_laudo_salvo, _console,
)
# FIM

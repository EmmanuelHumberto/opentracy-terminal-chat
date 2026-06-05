#!/bin/bash
cd /home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat
source .venv/bin/activate
python3 scripts/check_chat_end.py 2>&1

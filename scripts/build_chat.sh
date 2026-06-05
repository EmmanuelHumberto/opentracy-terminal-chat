#!/bin/bash
cd /home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat
source .venv/bin/activate 2>/dev/null || true
python3 scripts/gerar_final.py 2>&1
echo "---"
echo "Agora copiando para chat.py..."
cp app/chat_final.py app/chat.py
echo "OK"
wc -c app/chat.py

#!/usr/bin/env python3
"""Restaura o chat.py a partir do backup, removendo o encapsulamento JSON."""
import json
import sys
from pathlib import Path

backup_path = Path("/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app/chat.py.backup")
output_path = Path("/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app/chat.py")

# Le o backup como JSON e extrai o conteudo
try:
    data = json.loads(backup_path.read_text())
    content = data["content"]
    # O conteudo esta com escapes, precisa re-interpretar
    content = bytes(content, "utf-8").decode("unicode_escape")
except:
    # Se nao for JSON, le direto
    content = backup_path.read_text()

output_path.write_text(content)
print(f"✅ chat.py restaurado de {backup_path.name}")
print(f"   Tamanho: {len(content)} bytes")

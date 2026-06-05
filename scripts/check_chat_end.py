#!/usr/bin/env python3
"""Lê e imprime informação sobre o chat.py."""
with open("/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app/chat.py", "r") as f:
    lines = f.readlines()

print(f"Total de linhas: {len(lines)}")
print(f"Últimas 30 linhas:")
print("".join(lines[-30:]))

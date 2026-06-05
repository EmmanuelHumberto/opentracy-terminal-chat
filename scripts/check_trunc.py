#!/usr/bin/env python3
"""Mostra onde o chat.py foi truncado."""
with open("/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app/chat.py", "r") as f:
    lines = f.readlines()
print(f"Total: {len(lines)} linhas")
print(f"Últimas 5 linhas:")
for i, l in enumerate(lines[-5:]):
    print(f"  {len(lines)-5+i}: {l.rstrip()}")

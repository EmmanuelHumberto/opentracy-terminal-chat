#!/usr/bin/env python3
"""Mostra o ponto de truncatura do chat.py."""
with open("/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app/chat.py", "r") as f:
    lines = f.readlines()
print(f"Total: {len(lines)} linhas, {sum(len(l) for l in lines)} chars")
print("---ULTIMAS 10 LINHAS---")
for i, l in enumerate(lines[-10:]):
    print(f"{len(lines)-10+i}: {l}", end="")

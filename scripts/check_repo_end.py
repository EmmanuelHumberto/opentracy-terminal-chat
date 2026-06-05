#!/usr/bin/env python3
"""Lê e imprime o final do repositorio_medicoes.py."""
with open("/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app/repositorio_medicoes.py", "r") as f:
    lines = f.readlines()

print(f"Total de linhas: {len(lines)}")
print(f"Últimas 50 linhas:")
print("".join(lines[-50:]))

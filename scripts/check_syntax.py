#!/usr/bin/env python3
"""Verifica a sintaxe e o final do repositorio_medicoes.py."""
import sys
sys.path.insert(0, "/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat")

with open("/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app/repositorio_medicoes.py", "r") as f:
    conteudo = f.read()

print(f"Tamanho: {len(conteudo)} chars")
print(f"Ultimos 500 chars:")
print(repr(conteudo[-500:]))
print()
print("---")
print(conteudo[-500:])

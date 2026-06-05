#!/usr/bin/env python3
"""Mostra o final do arquivo repositorio_medicoes.py para debug."""
with open("/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app/repositorio_medicoes.py", "rb") as f:
    conteudo = f.read()

print(f"Tamanho total: {len(conteudo)} bytes")
print(f"Ultimos 3000 bytes:")
print(conteudo[-3000:].decode("utf-8", errors="replace"))

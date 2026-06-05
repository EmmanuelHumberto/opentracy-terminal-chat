#!/usr/bin/env python3
"""Gera o chat.py completo a partir das partes."""
import os

base = "/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app"

partes = [
    "chat.py",         # parte 1
    "chat_p2_complete.py",  # parte 2
    "chat_p3.py",      # parte 3
]

conteudo_total = []
for nome in partes:
    caminho = os.path.join(base, nome)
    with open(caminho, "r") as f:
        conteudo = f.read()
    conteudo_total.append(conteudo)
    print(f"Lido {nome}: {len(conteudo)} chars")

final = "\n\n".join(conteudo_total)

destino = os.path.join(base, "chat_final.py")
with open(destino, "w") as f:
    f.write(final)

print(f"\nTotal: {len(final)} chars")
print(f"Escrito em: {destino}")
print(f"Primeiras 100 chars: {final[:100]}")
print(f"Ultimas 100 chars: {final[-100:]}")

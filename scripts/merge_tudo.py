#!/usr/bin/env python3
"""Junta todos os blocos do chat.py."""
import os, shutil

base = "/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app"

# Ordem dos blocos
blocos = [
    "chat.py",                # Parte 1: imports, classes, comandos basicos
    "chat_p2_complete.py",    # Parte 2: utilitarios de captura
    "chat_cmd_capturar.py",   # _cmd_capturar
    "chat_cmd_medicoes.py",   # _cmd_medicoes
    "chat_cmd_medicao.py",    # _cmd_medicao
    "chat_cmd_laudo.py",      # _cmd_laudo
    "chat_router_loop.py",    # build_router, run_chat_loop
]

conteudos = []
for nome in blocos:
    caminho = os.path.join(base, nome)
    if os.path.exists(caminho):
        with open(caminho, "r") as f:
            conteudos.append(f.read())
        print(f"Lido: {nome} ({len(conteudos[-1])} chars)")
    else:
        print(f"AVISO: {nome} nao encontrado!")

final = "\n\n".join(conteudos)

# Backup
shutil.copy2(os.path.join(base, "chat.py"), os.path.join(base, "chat.py.bak_final"))

# Escrever
with open(os.path.join(base, "chat.py"), "w") as f:
    f.write(final)

print(f"\nFEITO! chat.py = {len(final)} bytes")
print(f"Backup em: chat.py.bak_final")

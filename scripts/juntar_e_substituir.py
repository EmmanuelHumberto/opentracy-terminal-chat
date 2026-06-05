#!/usr/bin/env python3
"""Junta as partes e substitui o chat.py."""
import shutil, os

base = "/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app"
dest = os.path.join(base, "chat.py")

# Ler partes
with open(os.path.join(base, "chat.py"), "r") as f:
    p1 = f.read()
with open(os.path.join(base, "chat_p2.py"), "r") as f:
    p2 = f.read()
with open(os.path.join(base, "chat_p3.py"), "r") as f:
    p3 = f.read()

# Fazer backup
bak = dest + ".bak2"
shutil.copy2(dest, bak) if os.path.exists(dest) else None

# Escrever completo
completo = p1.strip() + "\n\n" + p2.strip() + "\n\n" + p3.strip() + "\n"
with open(dest, "w") as f:
    f.write(completo)

print(f"OK: {len(completo)} chars escritos em {dest}")
print(f"Backup em: {bak}")

#!/usr/bin/env python3
"""Junta as partes do chat.py em um unico arquivo."""
import os

base = "/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app"

with open(os.path.join(base, "chat.py"), "r") as f:
    p1 = f.read()

with open(os.path.join(base, "chat_p2.py"), "r") as f:
    p2 = f.read()

with open(os.path.join(base, "chat_p3.py"), "r") as f:
    p3 = f.read()

completo = p1 + "\n" + p2 + "\n" + p3

with open(os.path.join(base, "chat_completo.py"), "w") as f:
    f.write(completo)

print(f"Arquivo completo gerado: {len(completo)} chars")
print(f"Ultimas linhas:")
for line in completo.split("\n")[-5:]:
    print(f"  {line}")

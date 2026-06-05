#!/usr/bin/env python3
import sys, os
sys.path.insert(0, "/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat")

base = "/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app"

# Ler partes
with open(os.path.join(base, "chat.py"), "r") as f:
    p1 = f.read()
with open(os.path.join(base, "chat_p2.py"), "r") as f:
    p2 = f.read()
with open(os.path.join(base, "chat_p3.py"), "r") as f:
    p3 = f.read()

# Combinar
completo = p1.rstrip() + "\n\n" + p2 + "\n\n" + p3

# Salvar
dest = os.path.join(base, "chat.py")
with open(dest, "w") as f:
    f.write(completo)

print(f"OK: chat.py reescrito com {len(completo)} bytes")
print(f"Ultimas 3 linhas:")
for l in completo.strip().split("\n")[-3:]:
    print(f"  {l}")

import shutil, os, sys

base = "/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app"

# Ler as tres partes
with open(os.path.join(base, "chat.py"), "r") as f:
    p1 = f.read()

with open(os.path.join(base, "chat_p2_complete.py"), "r") as f:
    p2 = f.read()

with open(os.path.join(base, "chat_p3.py"), "r") as f:
    p3 = f.read()

# Juntar
full = p1.rstrip() + "\n\n" + p2 + "\n\n" + p3

# Backup
bak = os.path.join(base, "chat.py.bak3")
if os.path.exists(os.path.join(base, "chat.py")):
    shutil.copy2(os.path.join(base, "chat.py"), bak)

# Escrever
with open(os.path.join(base, "chat.py"), "w") as f:
    f.write(full)

print(f"OK: {len(full)} bytes escritos")
print(f"Backup: {bak}")

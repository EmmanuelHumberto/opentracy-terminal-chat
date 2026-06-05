import os, shutil

base = "/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app"

# Parte 1
with open(os.path.join(base, "chat.py"), "r") as f:
    p1 = f.read()

# Parte 2
with open(os.path.join(base, "chat_p2_complete.py"), "r") as f:
    p2 = f.read()

# Parte 3
with open(os.path.join(base, "chat_p3.py"), "r") as f:
    p3 = f.read()

# Merge
final = p1.rstrip() + "\n\n" + p2 + "\n\n" + p3

# Salvar
with open(os.path.join(base, "chat_final.py"), "w") as f:
    f.write(final)

# Copiar para chat.py
shutil.copy2(os.path.join(base, "chat_final.py"), os.path.join(base, "chat.py"))

print(f"FEITO! {len(final)} bytes")
print(f"chat.py atualizado com sucesso")

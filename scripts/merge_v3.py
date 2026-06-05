import os, shutil, sys
base = "/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app"
files = ["chat.py", "chat_utils_compact.py", "chat_captura_func.py", "chat_bloco_capturar.py", "chat_bloco_med.py", "chat_bloco_laudo.py", "chat_bloco_router.py"]
parts = []
for f in files:
    p = os.path.join(base, f)
    if os.path.exists(p):
        parts.append(open(p).read())
full = "\n\n".join(parts)
shutil.copy2(os.path.join(base, "chat.py"), os.path.join(base, "chat.py.bak_v3"))
open(os.path.join(base, "chat.py"), "w").write(full)
print(f"FEITO! {len(full)} bytes")

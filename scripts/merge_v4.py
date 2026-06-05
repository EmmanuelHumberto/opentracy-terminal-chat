#!/usr/bin/env python3
import os, shutil
base = "/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app"
files = ["chat.py", "chat_utils_compact.py", "chat_captura_func.py", "chat_bloco_capturar.py", "chat_bloco_med.py", "chat_bloco_laudo.py", "chat_bloco_router.py"]
parts = [open(os.path.join(base, f)).read() for f in files if os.path.exists(os.path.join(base, f))]
full = "\n\n".join(parts)
shutil.copy2(os.path.join(base, "chat.py"), os.path.join(base, "chat.py.bak_v4"))
open(os.path.join(base, "chat.py"), "w").write(full)
print(f"FEITO! {len(full)} bytes")

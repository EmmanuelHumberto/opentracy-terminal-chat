#!/usr/bin/env python3
import os, shutil
base = "/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app"
files = ["chat.py", "chat_utils_compact.py", "chat_captura_func.py", "chat_cmd_capturar.py", "chat_cmd_medicoes.py", "chat_cmd_medicao.py", "chat_cmd_laudo.py", "chat_router_loop.py"]
parts = [open(os.path.join(base, f)).read() for f in files if os.path.exists(os.path.join(base, f))]
full = "\n\n".join(parts)
shutil.copy2(os.path.join(base, "chat.py"), os.path.join(base, "chat.py.bak9"))
open(os.path.join(base, "chat.py"), "w").write(full)
print(f"FEITO! {len(full)} bytes")

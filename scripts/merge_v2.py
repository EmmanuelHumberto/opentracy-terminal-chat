import os, shutil
base = "/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app"
files = ["chat.py", "chat_utils_compact.py", "chat_captura_func.py", "chat_bloco_capturar.py", "chat_bloco_med.py", "chat_bloco_laudo.py", "chat_bloco_router.py"]
parts = []
for f in files:
    p = os.path.join(base, f)
    if os.path.exists(p):
        parts.append(open(p).read())
        print(f"OK: {f} ({len(parts[-1])} chars)")
    else:
        print(f"FALTA: {f}")
full = "\n\n".join(parts)
shutil.copy2(os.path.join(base, "chat.py"), os.path.join(base, "chat.py.bak_v2"))
open(os.path.join(base, "chat.py"), "w").write(full)
print(f"\nFEITO! {len(full)} bytes")

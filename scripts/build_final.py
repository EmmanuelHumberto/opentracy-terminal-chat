import os, shutil
base = "/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app"

# Lista de arquivos na ordem correta
files = [
    "chat.py",              # parte 1
    "chat_utils_compact.py", # _perguntar_opcao, _validar_snapshots, _verificar_conexao_serial
    "chat_captura_func.py",  # _executar_captura_com_tratamento
    "chat_cmd_capturar.py",  # _cmd_capturar
    "chat_cmd_medicoes.py",  # _cmd_medicoes
    "chat_cmd_medicao.py",   # _cmd_medicao
    "chat_cmd_laudo.py",     # _cmd_laudo
    "chat_router_loop.py",   # build_router, run_chat_loop
]

# Ler e concatenar
parts = []
for fname in files:
    path = os.path.join(base, fname)
    if os.path.exists(path):
        with open(path, "r") as f:
            parts.append(f.read())
        print(f"OK: {fname}")
    else:
        print(f"FALTA: {fname}")

full = "\n\n".join(parts)

# Backup
bak = os.path.join(base, "chat.py.bak7")
shutil.copy2(os.path.join(base, "chat.py"), bak)

# Escrever
with open(os.path.join(base, "chat.py"), "w") as f:
    f.write(full)

print(f"\nFEITO! {len(full)} bytes em chat.py")
print(f"Backup: {bak}")

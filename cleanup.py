import os, shutil
base = '/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat'
os.chdir(base)
for f in ['run_git.py', 'run_git.sh', 'run_checks.py', 'run_tests.py', 'check_imports.py']:
    for ext in ['', '.backup']:
        p = os.path.join(base, f + ext)
        if os.path.exists(p):
            os.remove(p)
            print(f"Removido: {f}{ext}")
egg_dir = os.path.join(base, 'ligadoai_terminal_chat.egg-info')
if os.path.isdir(egg_dir):
    shutil.rmtree(egg_dir)
    print("Removido: egg-info")
print("Limpeza concluida")

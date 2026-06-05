python3 -c "
import os, shutil
base = '/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app'
files = ['chat.py', 'chat_utils_compact.py', 'chat_captura_func.py', 'chat_cmd_capturar.py', 'chat_cmd_medicoes.py', 'chat_cmd_medicao.py', 'chat_cmd_laudo.py', 'chat_router_loop.py']
parts = []
for f in files:
    p = os.path.join(base, f)
    if os.path.exists(p):
        parts.append(open(p).read())
full = '\n\n'.join(parts)
shutil.copy2(os.path.join(base, 'chat.py'), os.path.join(base, 'chat.py.bak10'))
open(os.path.join(base, 'chat.py'), 'w').write(full)
print(f'FEITO! {len(full)} bytes')
"
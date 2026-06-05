python3 -c "
import os, shutil
base = '/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app'
with open(os.path.join(base, 'chat.py'), 'r') as f: p1 = f.read()
with open(os.path.join(base, 'chat_p2_complete.py'), 'r') as f: p2 = f.read()
with open(os.path.join(base, 'chat_p3.py'), 'r') as f: p3 = f.read()
final = p1.rstrip() + '\n\n' + p2 + '\n\n' + p3
shutil.copy2(os.path.join(base, 'chat.py'), os.path.join(base, 'chat.py.bak6'))
with open(os.path.join(base, 'chat.py'), 'w') as f: f.write(final)
print(f'OK: {len(final)} bytes')
"
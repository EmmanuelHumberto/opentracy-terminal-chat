import sys, re
path = '/home/hiatus/Projetos/ligadotattoo/OpenTracy/runtime/server.py'
with open(path) as f:
    data = f.read()
for m in re.finditer(r'^.*secret.*$', data, re.MULTILINE | re.IGNORECASE):
    print(m.group())
sys.stdout.flush()

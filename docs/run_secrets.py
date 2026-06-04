import subprocess, sys
r = subprocess.run([sys.executable, '-c', 'import re\nwith open("/home/hiatus/Projetos/ligadotattoo/OpenTracy/runtime/server.py") as f:\n data = f.read()\nfor m in re.finditer(r"^.*secret.*$", data, re.M|re.I):\n print(m.group())'], capture_output=True, text=True, timeout=30)
print(r.stdout)
if r.stderr:
    print("STDERR:", r.stderr[:2000])

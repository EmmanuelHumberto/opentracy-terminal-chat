import subprocess, sys, os
os.chdir('/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/docs')
result = subprocess.run([sys.executable, 'analyze_secrets.py'], capture_output=True, text=True, timeout=30)
print(result.stdout)
if result.stderr:
    print(result.stderr[:2000])

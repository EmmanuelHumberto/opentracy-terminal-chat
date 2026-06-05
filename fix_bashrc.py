#!/usr/bin/env python3
bashrc_path = "/home/hiatus/.bashrc"

with open(bashrc_path) as f:
    content = f.read()

target = '. "$HOME/.local/bin/env"'
idx = content.find(target)
if idx > 0:
    end_of_line = idx + len(target)
    content = content[:end_of_line] + "\n"

content += """
# ============================================================
# LigadoAI Terminal Chat
# ============================================================
source /home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/aliases.sh
"""

with open(bashrc_path, 'w') as f:
    f.write(content)

print("PRONTO! ~/.bashrc atualizado.")
print("Agora execute no terminal:")
print("  source ~/.bashrc")
print("  consulta")

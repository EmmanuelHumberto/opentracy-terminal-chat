#!/bin/bash
# Restaura arquivos via git
cd /home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat
git checkout -- app/chat.py app/captura_serial.py app/formulario_coleta.py app/laudo_tecnico.py app/repositorio_medicoes.py 2>/dev/null && echo "Restaurado do git" || echo "Git nao funcionou, tentando backups..."

# Se git nao funcionar, tenta copiar backups que estao bons
for f in chat.py captura_serial.py formulario_coleta.py laudo_tecnico.py repositorio_medicoes.py; do
    if [ -f "app/$f.backup" ]; then
        cp "app/$f.backup" "app/$f"
        echo "Copiado backup de $f"
    fi
done
echo "Concluido"

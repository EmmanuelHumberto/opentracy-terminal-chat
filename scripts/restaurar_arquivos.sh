#!/bin/bash
# ============================================================================
# Restaura arquivos Python corrompidos (formato JSON) para formato .py puro
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Restaurando arquivos corrompidos..."
echo ""

for arquivo in "chat.py" "captura_serial.py" "formulario_coleta.py" "laudo_tecnico.py" "repositorio_medicoes.py"; do
    original="$PROJECT_DIR/app/$arquivo"
    backup="$PROJECT_DIR/app/$arquivo.backup"
    
    if [ -f "$backup" ]; then
        echo "📄 $arquivo"
        
        # Verifica se o arquivo comeca com { (JSON)
        if head -c 1 "$original" | grep -q '{'; then
            echo "   ⚠️  Corrompido (formato JSON). Restaurando do backup..."
            
            # Tenta extrair o conteudo do JSON
            python3 << 'PYEOF'
import json, sys, os

arquivo = sys.argv[1]
backup = sys.argv[2]

try:
    data = json.loads(open(arquivo).read())
    content = data.get('content', '')
    # Remove os escapes
    content = content.encode('utf-8').decode('unicode_escape')
    open(arquivo, 'w').write(content)
    print(f'   ✅ Restaurado ({len(content)} bytes)')
except Exception as e:
    print(f'   ⚠️  Erro ao extrair JSON: {e}')
    print('   Copiando backup diretamente...')
    import shutil
    shutil.copy2(backup, arquivo)
    print(f'   ✅ Backup copiado')
PYEOF
            python3 -c "
import json, sys
arquivo = '$original'
backup = '$backup'
try:
    data = json.loads(open(arquivo).read())
    content = data.get('content', '')
    content = content.encode('utf-8').decode('unicode_escape')
    open(arquivo, 'w').write(content)
    print(f'   ✅ Restaurado ({len(content)} bytes)')
except Exception as e:
    print(f'   ⚠️  Erro: {e}')
    import shutil
    shutil.copy2(backup, arquivo)
    print(f'   ✅ Backup copiado')
"
        else:
            echo "   ✅ OK (formato Python puro)"
        fi
    else
        echo "   ⚠️  Sem backup para $arquivo"
    fi
done

echo ""
echo "✅ Restauracao concluida!"

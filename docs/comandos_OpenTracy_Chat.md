# 1. Ativar o ambiente virtual
cd /home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat
source .venv/bin/activate

# 2. Instalar dependencias da Fase 4 (se ainda não instalou)
pip install pymupdf python-docx openpyxl

# 3. Copiar seus PDFs para a pasta knowledge
cp /caminho/para/seu/pdf1.pdf knowledge/
cp /caminho/para/seu/pdf2.pdf knowledge/

# 4. Verificar se os arquivos estão lá
ls -la knowledge/

# 5. Iniciar o chat
python3 -m app.main
```

**Dentro do chat:**

```text
/indexar
```

Se quiser testar a conversão sem entrar no chat:

```bash
# Teste rapido da conversao
python3 -c "
from ligadoai_tools.document_server import convert_directory
from pathlib import Path
r = convert_directory(Path('knowledge'), Path('knowledge_md'))
print(f'Convertidos: {r[\"converted\"]}, Erros: {r[\"errors\"]}')
for res in r.get('results', []):
    print(f'  OK: {res[\"source\"]}')
"

# Ver o resultado
ls -la knowledge_md/


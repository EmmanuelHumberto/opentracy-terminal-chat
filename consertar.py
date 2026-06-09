#!/usr/bin/env python3
import json, re, sys
from pathlib import Path

app = Path(__file__).parent / "app"

for arq in ["chat.py","captura_serial.py","formulario_coleta.py","laudo_tecnico.py","repositorio_medicoes.py"]:
    p = app / arq
    if not p.exists(): continue
    txt = p.read_text()
    if txt.strip().startswith("{"):
        try:
            # Extrai o content bruto (pode estar truncado)
            m = re.search(r'"content":\s*"(.*)', txt, re.DOTALL)
            if m:
                raw = m.group(1)
                # Remove o ultimo '"' e fecha chaves se existir
                raw = raw.rstrip('"}')
                # Decode dos escapes
                content = raw.encode("utf-8").decode("unicode_escape")
                p.write_text(content)
                print(f"OK {arq}: {len(content)} bytes")
            else:
                print(f"FAIL {arq}: nao achou content")
        except Exception as e:
            print(f"ERRO {arq}: {e}")
    else:
        print(f"OK {arq}: ja esta puro")

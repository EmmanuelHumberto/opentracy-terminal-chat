#!/usr/bin/env python3
"""Conserta arquivos .py que foram salvos como JSON encapsulado."""
import json
import shutil
from pathlib import Path

APP_DIR = Path("/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app")

arquivos = [
    "chat.py",
    "captura_serial.py", 
    "formulario_coleta.py",
    "laudo_tecnico.py",
    "repositorio_medicoes.py",
]

for nome in arquivos:
    original = APP_DIR / nome
    backup = APP_DIR / f"{nome}.backup"
    
    if not original.exists():
        print(f"❌ {nome}: arquivo nao encontrado")
        continue
    
    conteudo = original.read_text()
    
    # Verifica se comeca com { (JSON)
    if conteudo.strip().startswith("{"):
        print(f"⚠️  {nome}: formato JSON detectado")
        
        try:
            data = json.loads(conteudo)
            # Pega o content e faz decode dos escapes
            raw = data.get("content", "")
            # Converte \\n para \n, \\" para ", etc.
            codigo = raw.encode("utf-8").decode("unicode_escape")
            
            # Salva como .py puro
            original.write_text(codigo)
            print(f"   ✅ Restaurado! {len(codigo)} bytes")
        except Exception as e:
            print(f"   ❌ Erro ao processar JSON: {e}")
            if backup.exists():
                print(f"   ↪ Copiando backup...")
                shutil.copy2(backup, original)
                print(f"   ✅ Backup copiado")
    else:
        print(f"✅ {nome}: OK (Python puro)")

print("\n✅ Concluido!")

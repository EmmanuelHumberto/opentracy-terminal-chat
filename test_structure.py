#!/usr/bin/env python3
"""Testa se a estrutura de pastas e preservada na conversao."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

print("=" * 60)
print("Teste: Preservacao de estrutura de pastas")
print("=" * 60)

# Importa (o __init__.py aplica os patches automaticamente)
from ligadoai_tools.document_server import convert_directory

# Cria estrutura de teste
with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    
    # Cria knowledge/ com subpastas
    knowledge = tmp_path / "knowledge"
    knowledge_md = tmp_path / "knowledge_md"
    
    # Cria estrutura de pastas
    (knowledge / "01-motores" / "coreless").mkdir(parents=True)
    (knowledge / "03-maquinas" / "rotativa").mkdir(parents=True)
    (knowledge / "09-diagnosticos").mkdir(parents=True)
    
    # Cria arquivos de teste
    (knowledge / "01-motores" / "coreless" / "motor-2016.md").write_text(
        "# Motor 2016\n\nEspecificacoes do motor coreless 2016.\n", encoding="utf-8"
    )
    (knowledge / "03-maquinas" / "rotativa" / "cheyenne-hawk.md").write_text(
        "# Cheyenne Hawk Pen\n\nManual da maquina rotativa.\n", encoding="utf-8"
    )
    (knowledge / "09-diagnosticos" / "vibracao-excessiva.md").write_text(
        "# Vibracao Excessiva\n\nCausas e solucoes.\n", encoding="utf-8"
    )
    (knowledge / "manual-geral.md").write_text(
        "# Manual Geral\n\nConteudo na raiz.\n", encoding="utf-8"
    )
    
    # Executa a conversao
    print("\nExecutando convert_directory...")
    result = convert_directory(knowledge, knowledge_md, recursive=True)
    
    print(f"\nResultado: {result.get('converted')} arquivos convertidos")
    
    # Verifica a estrutura gerada
    print("\nEstrutura gerada em knowledge_md/:")
    for f in sorted(knowledge_md.rglob("*")):
        if f.is_file():
            rel = f.relative_to(knowledge_md)
            print(f"  {rel}")
    
    # Verifica se a estrutura foi preservada
    expected_files = [
        knowledge_md / "01-motores" / "coreless" / "motor-2016.md",
        knowledge_md / "03-maquinas" / "rotativa" / "cheyenne-hawk.md",
        knowledge_md / "09-diagnosticos" / "vibracao-excessiva.md",
        knowledge_md / "manual-geral.md",
    ]
    
    print("\nVerificacao:")
    all_ok = True
    for expected in expected_files:
        exists = expected.exists()
        status = "✅" if exists else "❌"
        if not exists:
            all_ok = False
        print(f"  {status} {expected.relative_to(knowledge_md)}")
    
    if all_ok:
        print("\n✅ Teste PASSOU - Estrutura de pastas preservada!")
    else:
        print("\n❌ Teste FALHOU - Alguns arquivos na estrutura errada")

print("=" * 60)

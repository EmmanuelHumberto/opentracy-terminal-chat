#!/usr/bin/env python3
"""Testa se o suporte a .zip funciona corretamente."""

import sys
from pathlib import Path

# Adiciona o diretorio raiz ao path
sys.path.insert(0, str(Path(__file__).resolve().parent))

print("Testando import do document_server...")

# Importa (o __init__.py aplica o patch automaticamente)
from ligadoai_tools.document_server import (
    SUPPORTED_EXTENSIONS,
    convert_file,
    convert_directory,
    convert_zip,
)

print(f"SUPPORTED_EXTENSIONS: {list(SUPPORTED_EXTENSIONS.keys())}")
print(f"  .zip suportado: {'.zip' in SUPPORTED_EXTENSIONS}")
print(f"convert_directory: {convert_directory}")
print(f"convert_zip: {convert_zip}")
print()

# Testa com um zip de exemplo
import tempfile
import zipfile

# Cria um zip de teste
with tempfile.TemporaryDirectory() as tmp:
    # Cria arquivo de teste
    test_md = Path(tmp) / "teste.md"
    test_md.write_text("# Teste\n\nConteudo de teste.\n", encoding="utf-8")

    # Cria zip
    zip_path = Path(tmp) / "teste.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(test_md, "teste.md")

    # Cria output dir
    output_dir = Path(tmp) / "output"
    output_dir.mkdir()

    # Testa convert_file com zip
    result = convert_file(zip_path, output_dir)
    print(f"convert_file com .zip: {result.get('success')}")
    print(f"  converted_count: {result.get('converted_count')}")
    print(f"  errors_count: {result.get('errors_count')}")

    # Verifica se o markdown foi gerado
    output_md = output_dir / "teste.md"
    print(f"  arquivo gerado: {output_md.exists()}")

print()
print("Teste concluido!")

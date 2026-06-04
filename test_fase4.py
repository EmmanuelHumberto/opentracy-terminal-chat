"""Teste rapido da Fase 4 - conversao de documentos."""
import sys
from pathlib import Path

# Adiciona o diretorio raiz ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ligadoai_tools.document_server import convert_directory

source_dir = Path("knowledge")
output_dir = Path("knowledge_md")

print(f"Source: {source_dir.resolve()}")
print(f"Output: {output_dir.resolve()}")
print()

if not source_dir.is_dir():
    print(f"ERRO: diretorio {source_dir} nao encontrado!")
    sys.exit(1)

result = convert_directory(source_dir, output_dir, recursive=True)

print(f"Total arquivos: {result['total_files']}")
print(f"Convertidos: {result['converted']}")
print(f"Erros: {result['errors']}")
print(f"Falhas parciais: {result['partials']}")
print(f"Total chars: {result['total_chars']}")
print()

if result['converted'] > 0:
    print("Arquivos convertidos:")
    for r in result['results']:
        print(f"  ✅ {r['source']} -> {r['output']} ({r['chars']} chars)")

if result['error_details']:
    print("\nErros:")
    for e in result['error_details']:
        print(f"  ❌ {e.get('error', {}).get('message', 'desconhecido')}")

if result['partial_details']:
    print("\nAvisos de falha parcial:")
    for p in result['partial_details']:
        print(f"  ⚠️  {p.get('partial', {}).get('detail', '')}")

print("\nConteudo gerado em knowledge_md/:")
for f in sorted(output_dir.glob("*")):
    if f.is_file():
        print(f"  📄 {f.name} ({f.stat().st_size} bytes)")

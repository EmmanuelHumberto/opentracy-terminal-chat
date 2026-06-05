#!/usr/bin/env python3
"""Patch para adicionar suporte a .zip no document_server.py.

Uso: python patch_zip_support.py
"""

import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DOC_SERVER = SCRIPT_DIR / "document_server.py"

# Código da funcao convert_zip para adicionar
CONVERT_ZIP_CODE = '''
# ---------------------------------------------------------------------------
# .zip (extrai e converte arquivos internos)
# ---------------------------------------------------------------------------

def convert_zip(source: Path, output_dir: Path) -> dict[str, Any]:
    """Extrai um arquivo ZIP e converte todos os arquivos suportados.

    Para cada arquivo dentro do ZIP com extensao suportada, aplica o
    conversor correspondente e salva o Markdown no diretorio de saida.

    Retorna:
      - success: True se pelo menos um arquivo foi convertido
      - converted_files: lista de resultados individuais
      - errors_files: lista de erros internos
      - unsupported: lista de arquivos ignorados (extensao nao suportada)
    """
    try:
        import zipfile
    except ImportError:
        return _conversion_failed("zipfile nao disponivel (stdlib).")

    if not source.is_file():
        return _conversion_failed(f"Arquivo ZIP nao encontrado: {source}")

    # Abre o ZIP
    try:
        zf = zipfile.ZipFile(source, 'r')
    except zipfile.BadZipFile:
        return _conversion_failed(f"Arquivo ZIP invalido ou corrompido: {source.name}")
    except Exception as exc:
        return _conversion_failed(f"Erro ao abrir ZIP: {exc}")

    zip_name = source.stem
    converted_files: list[dict[str, Any]] = []
    errors_files: list[dict[str, Any]] = []
    unsupported: list[str] = []
    total_chars = 0

    # Extrai para diretorio temporario para processar cada arquivo
    with tempfile.TemporaryDirectory(prefix=f"zip_{zip_name}_") as tmp_dir:
        tmp_path = Path(tmp_dir)

        for info in zf.infolist():
            if info.is_dir():
                continue

            filename = info.filename
            ext = Path(filename).suffix.lower()

            # Ignora arquivos ocultos / __MACOSX / etc
            if "/__MACOSX" in filename or filename.startswith("__MACOSX"):
                continue
            if "/." in filename or filename.startswith("."):
                continue

            if ext not in SUPPORTED_EXTENSIONS:
                unsupported.append(filename)
                continue

            # Extrai o arquivo para diretorio temporario
            try:
                zf.extract(info, tmp_path)
            except Exception as exc:
                errors_files.append({
                    "file": filename,
                    "error": str(exc),
                })
                continue

            extracted = tmp_path / filename

            if not extracted.is_file():
                errors_files.append({
                    "file": filename,
                    "error": "Arquivo extraido nao encontrado",
                })
                continue

            # Aplica o conversor correspondente
            try:
                result = SUPPORTED_EXTENSIONS[ext](extracted, output_dir)
                if result.get("success"):
                    converted_files.append(result)
                    total_chars += result.get("chars", 0)
                else:
                    errors_files.append({
                        "file": filename,
                        "error": result.get("error", {}).get("message", "Falha na conversao"),
                    })
            except Exception as exc:
                errors_files.append({
                    "file": filename,
                    "error": str(exc),
                })

    zf.close()

    result: dict[str, Any] = {
        "success": len(converted_files) > 0,
        "source": str(source),
        "output": str(output_dir),
        "format": "zip",
        "converted_files": converted_files,
        "converted_count": len(converted_files),
        "errors_count": len(errors_files),
        "unsupported_count": len(unsupported),
        "total_chars": total_chars,
    }

    if errors_files:
        result["errors_files"] = errors_files
    if unsupported:
        result["unsupported_files"] = unsupported
    if len(converted_files) == 0 and len(errors_files) > 0:
        result["partial"] = _conversion_partial(
            f"Nenhum arquivo convertido. {len(errors_files)} erro(s), "
            f"{len(unsupported)} arquivo(s) ignorados."
        )

    return result
'''

# Codigo para adicionar no SUPPORTED_EXTENSIONS
ZIP_EXTRA = '    ".zip": convert_zip,\n'


def main():
    content = DOC_SERVER.read_text(encoding="utf-8")

    # Verifica se ja tem suporte a zip
    if '".zip"' in content:
        print("Suporte a .zip ja existe no arquivo.")
        return

    # Verifica se a funcao convert_zip ja existe
    if "def convert_zip" in content:
        print("Funcao convert_zip ja existe.")
        return

    # 1. Adiciona o import do tempfile se nao existir
    if "import tempfile" not in content:
        content = content.replace(
            "from typing import Any, Optional",
            "from typing import Any, Optional\nimport tempfile",
        )

    # 2. Adiciona a funcao convert_zip antes do SUPPORTED_EXTENSIONS
    # Procura pelo inicio do dicionario SUPPORTED_EXTENSIONS
    marker = "SUPPORTED_EXTENSIONS = {"
    if marker in content:
        content = content.replace(marker, CONVERT_ZIP_CODE + "\n\n" + marker)
        print("Funcao convert_zip adicionada.")
    else:
        print("ERRO: Nao encontrou SUPPORTED_EXTENSIONS no arquivo.")
        return

    # 3. Adiciona ".zip" no dicionario SUPPORTED_EXTENSIONS
    # Procura a ultima entrada do dicionario antes do fechamento
    # Vamos adicionar depois de ".tif": convert_image,
    zip_marker = '".tif": convert_image,'
    if zip_marker in content:
        content = content.replace(zip_marker, zip_marker + "\n" + ZIP_EXTRA)
        print("Registro .zip adicionado ao SUPPORTED_EXTENSIONS.")
    else:
        print("ERRO: Nao encontrou marcador .tif no SUPPORTED_EXTENSIONS.")
        return

    # 4. Atualiza docstring
    content = content.replace(
        "  - .jpg/.png/.bmp/.tiff → OCR com Tesseract",
        "  - .jpg/.png/.bmp/.tiff → OCR com Tesseract\n  - .zip        → extrai e converte arquivos suportados internamente",
    )

    DOC_SERVER.write_text(content, encoding="utf-8")
    print("Patch aplicado com sucesso!")
    print(f"Arquivo: {DOC_SERVER}")


if __name__ == "__main__":
    main()

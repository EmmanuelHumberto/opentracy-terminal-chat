# -*- coding: utf-8 -*-
"""Patch para adicionar suporte a .zip no document_server.py.

A funcao convert_zip e o registro em SUPPORTED_EXTENSIONS serao
adicionados ao final do arquivo document_server.py.
"""

import os
import tempfile
from pathlib import Path
from typing import Any

from ligadoai_tools.safety import error_response


def _conversion_partial(detail: str = "") -> dict:
    return error_response(
        "conversion_partial",
        "Conversor extraiu parte do documento.",
        recoverable=True,
        detail=detail,
    )


def _conversion_failed(detail: str = "") -> dict:
    return error_response(
        "conversion_failed",
        "Conversor nao conseguiu processar o arquivo.",
        recoverable=False,
        detail=detail,
    )


# Importa os conversores existentes
from ligadoai_tools.document_server import (
    SUPPORTED_EXTENSIONS,
    convert_md, convert_image, convert_pdf,
    convert_docx, convert_xlsx,
)


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


# Registra o conversor de ZIP
SUPPORTED_EXTENSIONS[".zip"] = convert_zip

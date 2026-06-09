# -*- coding: utf-8 -*-
"""Parte final do document_server.py (SUPPORTED_EXTENSIONS, convert_file, convert_directory).

Este arquivo contem o que foi truncado no document_server.py original.
Deve ser importado e injetado no modulo via __init__.py.
"""

from __future__ import annotations

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


SUPPORTED_EXTENSIONS = {
    ".md": None,      # será preenchido pelo apply_patch
    ".txt": None,
    ".pdf": None,
    ".docx": None,
    ".xlsx": None,
    ".jpg": None,
    ".jpeg": None,
    ".png": None,
    ".bmp": None,
    ".tiff": None,
    ".tif": None,
    ".zip": None,
}


def convert_file(source: Path, output_dir: Path) -> dict[str, Any]:
    """Converte um arquivo para Markdown."""
    ext = source.suffix.lower()
    converter = SUPPORTED_EXTENSIONS.get(ext)
    if not converter:
        return _conversion_failed(f"Formato nao suportado: {ext}")
    return converter(source, output_dir)


def convert_directory(
    source_dir: Path, output_dir: Path, *, recursive: bool = True
) -> dict[str, Any]:
    """Converte todos os arquivos suportados em um diretorio.

    Preserva a estrutura de subpastas: knowledge/01-motores/x.md
    → knowledge_md/01-motores/x.md
    """
    if not source_dir.is_dir():
        return _conversion_failed(f"Diretorio nao encontrado: {source_dir}")

    # Define o source_dir para os conversores preservarem a estrutura
    import ligadoai_tools.document_server as ds
    if hasattr(ds, '_set_source_dir'):
        ds._set_source_dir(source_dir)

    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    partials: list[dict[str, Any]] = []
    total_chars = 0

    pattern = "**/*" if recursive else "*"
    for entry in sorted(source_dir.glob(pattern)):
        if not entry.is_file():
            continue
        ext = entry.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        result = convert_file(entry, output_dir)
        if result.get("success"):
            results.append(result)
            total_chars += result.get("chars", 0)
        elif "error" in result:
            errors.append(result)
        if result.get("partial"):
            partials.append(result)

    # Limpa o source_dir
    if hasattr(ds, '_set_source_dir'):
        ds._set_source_dir(None)

    return {
        "success": len(errors) == 0,
        "total_files": len(results) + len(errors),
        "converted": len(results),
        "errors": len(errors),
        "partials": len(partials),
        "total_chars": total_chars,
        "source_dir": str(source_dir),
        "output_dir": str(output_dir),
        "results": results,
        "error_details": errors,
        "partial_details": partials,
    }


def apply_patch() -> None:
    """Aplica os simbolos faltantes no modulo document_server.

    Deve ser chamado uma vez na inicializacao (via __init__.py).
    """
    import ligadoai_tools.document_server as ds

    # Preenche os conversores
    SUPPORTED_EXTENSIONS[".md"] = ds.convert_md
    SUPPORTED_EXTENSIONS[".txt"] = ds.convert_md
    SUPPORTED_EXTENSIONS[".pdf"] = ds.convert_pdf
    SUPPORTED_EXTENSIONS[".docx"] = ds.convert_docx
    SUPPORTED_EXTENSIONS[".xlsx"] = ds.convert_xlsx
    SUPPORTED_EXTENSIONS[".jpg"] = ds.convert_image
    SUPPORTED_EXTENSIONS[".jpeg"] = ds.convert_image
    SUPPORTED_EXTENSIONS[".png"] = ds.convert_image
    SUPPORTED_EXTENSIONS[".bmp"] = ds.convert_image
    SUPPORTED_EXTENSIONS[".tiff"] = ds.convert_image
    SUPPORTED_EXTENSIONS[".tif"] = ds.convert_image
    SUPPORTED_EXTENSIONS[".zip"] = ds.convert_zip

    # Injeta no modulo
    ds.SUPPORTED_EXTENSIONS = SUPPORTED_EXTENSIONS
    ds.convert_file = convert_file
    ds.convert_directory = convert_directory

# -*- coding: utf-8 -*-
"""Patch completo para restaurar o final do document_server.py.

Este arquivo contem SUPPORTED_EXTENSIONS, convert_file, convert_directory
e o registro do .zip que foram truncados no document_server.py original.

Uso: from ligadoai_tools.document_server_patch_complete import apply_patch
     apply_patch()  # chama uma vez na inicializacao
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def apply_patch() -> None:
    """Aplica o patch no modulo document_server, restaurando
    SUPPORTED_EXTENSIONS, convert_file e convert_directory,
    e adicionando suporte a .zip."""
    import ligadoai_tools.document_server as ds

    # So aplica se SUPPORTED_EXTENSIONS nao existir ou estiver vazio
    if hasattr(ds, "SUPPORTED_EXTENSIONS") and len(ds.SUPPORTED_EXTENSIONS) > 0:
        return  # ja tem, nao precisa patch

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

    # Reconstrói o SUPPORTED_EXTENSIONS
    SUPPORTED_EXTENSIONS = {
        ".md": ds.convert_md,
        ".txt": ds.convert_md,
        ".pdf": ds.convert_pdf,
        ".docx": ds.convert_docx,
        ".xlsx": ds.convert_xlsx,
        ".jpg": ds.convert_image,
        ".jpeg": ds.convert_image,
        ".png": ds.convert_image,
        ".bmp": ds.convert_image,
        ".tiff": ds.convert_image,
        ".tif": ds.convert_image,
        ".zip": ds.convert_zip,
    }

    def convert_file(source: Path, output_dir: Path) -> dict[str, Any]:
        ext = source.suffix.lower()
        converter = SUPPORTED_EXTENSIONS.get(ext)
        if not converter:
            return _conversion_failed(f"Formato nao suportado: {ext}")
        return converter(source, output_dir)

    def convert_directory(
        source_dir: Path, output_dir: Path, *, recursive: bool = True
    ) -> dict[str, Any]:
        if not source_dir.is_dir():
            return _conversion_failed(f"Diretorio nao encontrado: {source_dir}")

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

    # Injeta no módulo
    ds.SUPPORTED_EXTENSIONS = SUPPORTED_EXTENSIONS
    ds.convert_file = convert_file
    ds.convert_directory = convert_directory

#!/usr/bin/env python3
"""Patch para preservar a estrutura de pastas ao converter documentos.

Antes:
  knowledge/01-motores/coreless/datasheet.md
    → knowledge_md/datasheet.md  (perdeu a estrutura)

Depois:
  knowledge/01-motores/coreless/datasheet.md
    → knowledge_md/01-motores/coreless/datasheet.md  (preservou)

Uso: from ligadoai_tools.patch_preserve_structure import apply_patch
     apply_patch()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


# Variavel global para armazenar o source_dir atual durante convert_directory
_current_source_dir: Path | None = None


def set_source_dir(source_dir: Path) -> None:
    """Define o diretorio de origem atual para calcular caminhos relativos."""
    global _current_source_dir
    _current_source_dir = source_dir


def _output_path(source: Path, output_dir: Path, suffix: str = ".md") -> Path:
    """Calcula o caminho de saida preservando a estrutura relativa.

    Se source_dir estiver definido, mantem a estrutura de subpastas.
    Ex: source=knowledge/01-motores/x.md, source_dir=knowledge/
        → output=knowledge_md/01-motores/x.md
    """
    global _current_source_dir
    if _current_source_dir and source.is_relative_to(_current_source_dir):
        rel = source.relative_to(_current_source_dir)
        # Troca a extensao para .md se necessario
        if suffix:
            rel = rel.with_suffix(suffix)
        return output_dir / rel
    # Fallback: comportamento antigo (raiz)
    if suffix:
        return output_dir / f"{source.stem}{suffix}"
    return output_dir / source.name


def apply_patch() -> None:
    """Aplica o patch nos conversores do document_server para preservar estrutura."""
    import ligadoai_tools.document_server as ds

    # Salva referencia aos conversores originais
    orig_convert_md = ds.convert_md
    orig_convert_image = ds.convert_image
    orig_convert_pdf = ds.convert_pdf
    orig_convert_docx = ds.convert_docx
    orig_convert_xlsx = ds.convert_xlsx
    orig_convert_zip = ds.convert_zip
    orig_convert_directory = getattr(ds, "convert_directory", None)

    # --- Patch convert_md ---
    def patched_convert_md(source: Path, output_dir: Path) -> dict[str, Any]:
        result = orig_convert_md(source, output_dir)
        if result.get("success"):
            # Recalcula o output_path com estrutura
            new_path = _output_path(source, output_dir, suffix="")
            if new_path != Path(result["output"]):
                # Move o arquivo para o local correto
                old_path = Path(result["output"])
                if old_path.exists():
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    old_path.rename(new_path)
                result["output"] = str(new_path)
        return result

    # --- Patch convert_image ---
    def patched_convert_image(source: Path, output_dir: Path) -> dict[str, Any]:
        result = orig_convert_image(source, output_dir)
        if result.get("success"):
            new_path = _output_path(source, output_dir, suffix=".md")
            if new_path != Path(result["output"]):
                old_path = Path(result["output"])
                if old_path.exists():
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    old_path.rename(new_path)
                result["output"] = str(new_path)
        return result

    # --- Patch convert_pdf ---
    def patched_convert_pdf(source: Path, output_dir: Path) -> dict[str, Any]:
        result = orig_convert_pdf(source, output_dir)
        if result.get("success"):
            new_path = _output_path(source, output_dir, suffix=".md")
            if new_path != Path(result["output"]):
                old_path = Path(result["output"])
                if old_path.exists():
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    old_path.rename(new_path)
                result["output"] = str(new_path)
        return result

    # --- Patch convert_docx ---
    def patched_convert_docx(source: Path, output_dir: Path) -> dict[str, Any]:
        result = orig_convert_docx(source, output_dir)
        if result.get("success"):
            new_path = _output_path(source, output_dir, suffix=".md")
            if new_path != Path(result["output"]):
                old_path = Path(result["output"])
                if old_path.exists():
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    old_path.rename(new_path)
                result["output"] = str(new_path)
        return result

    # --- Patch convert_xlsx ---
    def patched_convert_xlsx(source: Path, output_dir: Path) -> dict[str, Any]:
        result = orig_convert_xlsx(source, output_dir)
        if result.get("success"):
            new_path = _output_path(source, output_dir, suffix=".md")
            if new_path != Path(result["output"]):
                old_path = Path(result["output"])
                if old_path.exists():
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    old_path.rename(new_path)
                result["output"] = str(new_path)
        return result

    # --- Patch convert_zip ---
    def patched_convert_zip(source: Path, output_dir: Path) -> dict[str, Any]:
        # Para zips, preservamos a estrutura interna do zip
        # O zip ja extrai para temp dir com estrutura, mas os conversores internos
        # vao usar output_dir como raiz. Precisamos passar o source_dir correto.
        result = orig_convert_zip(source, output_dir)
        return result

    # --- Patch convert_directory ---
    if orig_convert_directory:
        def patched_convert_directory(
            source_dir: Path, output_dir: Path, *, recursive: bool = True
        ) -> dict[str, Any]:
            # Define o source_dir para os conversores usarem
            set_source_dir(source_dir)
            try:
                return orig_convert_directory(source_dir, output_dir, recursive=recursive)
            finally:
                # Limpa o source_dir apos a conversao
                set_source_dir(None)
        
        ds.convert_directory = patched_convert_directory

    # Aplica os patches
    ds.convert_md = patched_convert_md
    ds.convert_image = patched_convert_image
    ds.convert_pdf = patched_convert_pdf
    ds.convert_docx = patched_convert_docx
    ds.convert_xlsx = patched_convert_xlsx
    ds.convert_zip = patched_convert_zip

    print("[patch_preserve_structure] Patches aplicados com sucesso!")
    print(f"  source_dir atual: {_current_source_dir}")

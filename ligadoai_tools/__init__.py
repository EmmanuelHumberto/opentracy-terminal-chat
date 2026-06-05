# LigadoAI MCP Tools

# 1. Aplica patch completo no document_server (restaura SUPPORTED_EXTENSIONS,
#    convert_file, convert_directory e adiciona suporte a .zip)
from ligadoai_tools.document_server_patch_complete import apply_patch as _apply_complete
_apply_complete()

# 2. Aplica patch para preservar estrutura de pastas ao converter
from ligadoai_tools.patch_preserve_structure import apply_patch as _apply_structure
_apply_structure()

# 3. Aplica patch de suporte a .zip (adiciona .zip ao SUPPORTED_EXTENSIONS)
try:
    import ligadoai_tools.document_server_zip_fix  # noqa: F401
except ImportError:
    pass

"""Testes para app/knowledge_syncer.py"""

from app.knowledge_syncer import _frontmatter_text, chunkar


def test_chunkar_termina_no_ultimo_chunk_com_overlap():
    texto = " ".join(f"palavra{i}" for i in range(120))

    chunks = chunkar(texto, chunk_size=120, overlap=30)

    assert chunks
    assert len(chunks) < 30
    assert chunks[-1] in texto


def test_chunkar_texto_curto_retorna_um_chunk():
    assert chunkar("texto curto", chunk_size=120, overlap=30) == ["texto curto"]


def test_frontmatter_text_converte_numero_para_texto():
    assert _frontmatter_text({"modelo": 1618}, "modelo", "desconhecido") == "1618"

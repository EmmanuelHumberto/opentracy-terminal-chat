"""Sincronizador de conhecimento: chunking + embedding + upsert no PostgreSQL.

Recebe documentos validados, divide em chunks, gera embeddings com modelo
multilingue e persiste no banco com deteccao de mudancas por hash.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Optional

import asyncpg

from app.config import BancoConfig, CorpusConfig
from app.validador_conhecimento import ResultadoValidacao


# ------------------------------------------------------------------ #
# Limpeza de chunks
# ------------------------------------------------------------------ #

# Linhas que sao metadados e nao acrescentam valor semantico ao embedding
_LINHAS_METADADO = re.compile(
    r"^\s*(<!--.*?-->|#+|\* \* \*|---+|\.\.\.)\s*$"
)

# Comentarios HTML inline
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def _limpar_chunk(texto: str) -> str:
    """Remove metadados e lixo de um chunk antes de embeddar.

    Remove:
    - Comentarios HTML (<!-- ... -->)
    - Linhas que sao apenas delimitadores (---, ***, ...)
    - Linhas que sao apenas headings vazios
    """
    texto = _HTML_COMMENT.sub("", texto)
    linhas = texto.split("\n")
    linhas_limpas = [
        linha for linha in linhas
        if linha.strip() and not _LINHAS_METADADO.match(linha)
    ]
    return "\n".join(linhas_limpas).strip()


# ------------------------------------------------------------------ #
# Chunker
# ------------------------------------------------------------------ #

def chunkar(
    texto: str,
    chunk_size: int = 256,
    overlap: int = 64,
) -> list[str]:
    """Divide um texto em chunks com overlap.

    Args:
        texto: Texto a ser dividido.
        chunk_size: Tamanho maximo de cada chunk em caracteres.
        overlap: Sobreposicao entre chunks consecutivos.

    Returns:
        Lista de strings, uma por chunk.
    """
    if not texto.strip():
        return []

    texto = texto.strip()
    if len(texto) <= chunk_size:
        return [texto]

    chunks: list[str] = []
    inicio = 0

    while inicio < len(texto):
        fim = min(inicio + chunk_size, len(texto))

        # Se nao for o ultimo chunk, tentar quebrar em uma quebra natural
        if fim < len(texto):
            # Procurar quebra de paragrafo ou frase perto do fim
            janela = texto[fim - min(80, chunk_size // 3):fim]
            for delim in ["\n\n", "\n", ". ", "! ", "? ", "; ", " "]:
                pos = janela.rfind(delim)
                if pos != -1:
                    fim = fim - len(janela) + pos + len(delim)
                    break

        chunk = texto[inicio:fim].strip()
        if chunk:
            # Limpar metadados/lixo do chunk
            chunk = _limpar_chunk(chunk)
            if chunk:
                chunks.append(chunk)

        if fim >= len(texto):
            break

        proximo_inicio = max(0, fim - overlap)
        if proximo_inicio <= inicio:
            proximo_inicio = fim
        inicio = proximo_inicio

    return chunks


# ------------------------------------------------------------------ #
# Calculo de hash de chunk (SHA-1, mesmo formato do ingest.py original)
# ------------------------------------------------------------------ #

def _hash_chunk(texto: str) -> str:
    """SHA-1 do texto do chunk (20 bytes hex = 40 chars)."""
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()


def _frontmatter_text(frontmatter: dict[str, Any], campo: str, default: str) -> str:
    """Normaliza campos textuais do frontmatter antes de gravar no PostgreSQL."""
    valor = frontmatter.get(campo, default)
    if valor is None:
        return default
    texto = str(valor).strip()
    return texto or default


# ------------------------------------------------------------------ #
# KnowledgeSyncer
# ------------------------------------------------------------------ #

class KnowledgeSyncer:
    """Sincroniza documentos validados para o PostgreSQL.

    Faz chunking, embedding e upsert por hash de conteudo.
    Usa o modelo de embedding configurado (multilingue por padrao).

    Uso:
        syncer = KnowledgeSyncer(config.banco, config.corpus)
        await syncer.conectar()
        try:
            doc_id = await syncer.sincronizar(resultado_validacao)
        finally:
            await syncer.desconectar()
    """

    def __init__(self, banco_config: BancoConfig, corpus_config: CorpusConfig):
        self._banco = banco_config
        self._corpus = corpus_config
        self._pool: Optional[asyncpg.Pool] = None
        self._embedder: Any = None

    # ------------------------------------------------------------------ #
    # Conexao
    # ------------------------------------------------------------------ #

    async def conectar(self) -> None:
        """Abre pool PostgreSQL. O embedder e carregado sob demanda no primeiro _embed()."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=self._banco.host,
                port=self._banco.port,
                database=self._banco.database,
                user=self._banco.user,
                password=self._banco.password,
                min_size=self._banco.min_connections,
                max_size=self._banco.max_connections,
            )

    def _carregar_embedder(self) -> None:
        """Carrega o modelo de embedding sob demanda, suprimindo barra de progresso.

        O modelo e baixado uma unica vez para models/embedder/ dentro do projeto.
        Assim sobrevive a formatacao da maquina — basta fazer backup do projeto.
        """
        if self._embedder is not None:
            return
        import os as _os
        from pathlib import Path as _Path
        from sentence_transformers import SentenceTransformer

        # Suprime barra de progresso do HuggingFace Hub (incompativel com interface Rich)
        _os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

        # Cache local dentro do projeto (sobrevive a formatacao se fizer backup)
        cache_dir = _Path(__file__).resolve().parent.parent / "models" / "embedder"
        cache_dir.mkdir(parents=True, exist_ok=True)

        self._embedder = SentenceTransformer(
            self._corpus.embedder_model,
            cache_folder=str(cache_dir),
        )

    async def desconectar(self) -> None:
        """Fecha pool PostgreSQL."""
        if self._pool:
            await self._pool.close()
            self._pool = None
        # O modelo de embedding fica em memoria — nao precisa fechar

    # ------------------------------------------------------------------ #
    # Embedding
    # ------------------------------------------------------------------ #

    def _embed(self, textos: list[str]) -> list[list[float]]:
        """Gera embeddings para uma lista de textos.

        Carrega o modelo de embedding sob demanda na primeira chamada.
        Processa em lotes de 32 para evitar picos de memoria.

        Returns:
            Lista de vetores, cada um com dimensao configurada (384).
        """
        self._carregar_embedder()

        batch_size = 32
        todos: list[list[float]] = []

        for i in range(0, len(textos), batch_size):
            lote = textos[i:i + batch_size]
            embeddings = self._embedder.encode(lote, normalize_embeddings=True)
            todos.extend(embeddings.tolist())

        return todos

    # ------------------------------------------------------------------ #
    # Upsert
    # ------------------------------------------------------------------ #

    async def sincronizar(self, resultado: ResultadoValidacao, source_path: str = "") -> Optional[str]:
        """Sincroniza um documento validado para o PostgreSQL.

        Args:
            resultado: Resultado da validacao (deve estar aprovado).
            source_path: Caminho do arquivo original (informativo).

        Returns:
            UUID do documento inserido/atualizado, ou None se rejeitado.
        """
        if not resultado.aprovado:
            return None

        if self._pool is None:
            raise RuntimeError("Pool PostgreSQL nao inicializado. Chame conectar() primeiro.")

        frontmatter = resultado.frontmatter
        conteudo = resultado.conteudo
        hash_conteudo = resultado.hash_conteudo
        fabricante = _frontmatter_text(frontmatter, "fabricante", "desconhecido")
        modelo = _frontmatter_text(frontmatter, "modelo", "desconhecido")
        tipo = _frontmatter_text(frontmatter, "tipo", "documento")

        async with self._pool.acquire() as conn:
            # Verificar se documento ja existe pelo hash
            existente = await conn.fetchrow(
                """SELECT id, n_chunks FROM documentos_conhecimento
                   WHERE hash_conteudo = $1""",
                hash_conteudo,
            )

            if existente:
                # Documento identico — apenas atualizar metadados e timestamp
                doc_id = existente["id"]
                await conn.execute(
                    """UPDATE documentos_conhecimento SET
                         fabricante = $2, modelo = $3, tipo = $4,
                         frontmatter = $5, source_path = $6,
                         indexado_em = NOW(), updated_at = NOW()
                       WHERE id = $1""",
                    doc_id,
                    fabricante,
                    modelo,
                    tipo,
                    _serialize_jsonb(frontmatter),
                    source_path,
                )
                return str(doc_id)

            # Documento novo ou modificado — chunkar, embeddar e inserir
            chunk_size = self._corpus.chunk_size
            overlap = self._corpus.overlap

            textos_chunks = chunkar(conteudo, chunk_size=chunk_size, overlap=overlap)
            if not textos_chunks:
                return None

            vetores = self._embed(textos_chunks)
            n_chunks = len(textos_chunks)

            # Inserir ou atualizar documento (apenas colunas universais)
            doc_id = await conn.fetchval(
                """INSERT INTO documentos_conhecimento
                     (fabricante, modelo, tipo, frontmatter, conteudo_md,
                      hash_conteudo, status_validacao, source_path, n_chunks,
                      indexado_em)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                   ON CONFLICT (id) DO UPDATE SET
                     fabricante = EXCLUDED.fabricante,
                     modelo = EXCLUDED.modelo,
                     tipo = EXCLUDED.tipo,
                     frontmatter = EXCLUDED.frontmatter,
                     conteudo_md = EXCLUDED.conteudo_md,
                     hash_conteudo = EXCLUDED.hash_conteudo,
                     status_validacao = EXCLUDED.status_validacao,
                     source_path = EXCLUDED.source_path,
                     n_chunks = EXCLUDED.n_chunks,
                     indexado_em = NOW(),
                     updated_at = NOW()
                   RETURNING id""",
                fabricante,
                modelo,
                tipo,
                _serialize_jsonb(frontmatter),
                conteudo,
                hash_conteudo,
                resultado.status,
                source_path,
                n_chunks,
            )

            # Remover chunks antigos e inserir novos
            await conn.execute(
                "DELETE FROM chunks WHERE documento_id = $1",
                doc_id,
            )

            for i, (texto_chunk, vetor) in enumerate(zip(textos_chunks, vetores)):
                chunk_id = _hash_chunk(texto_chunk)[:32]
                await conn.execute(
                    """INSERT INTO chunks
                         (chunk_id, documento_id, texto, vetor,
                          chunk_index, n_chunks, fabricante, modelo, tipo, metadata)
                       VALUES ($1, $2, $3, $4::FLOAT4[], $5, $6, $7, $8, $9, $10)
                       ON CONFLICT (chunk_id) DO NOTHING""",
                    chunk_id,
                    doc_id,
                    texto_chunk,
                    vetor,
                    i,
                    n_chunks,
                    fabricante,
                    modelo,
                    tipo,
                    _serialize_jsonb({
                        "fabricante": fabricante,
                        "modelo": modelo,
                        "tipo": tipo,
                        "source": source_path,
                    }),
                )

            return str(doc_id)

    # ------------------------------------------------------------------ #
    # Leitura para reload
    # ------------------------------------------------------------------ #

    async def listar_documentos(self) -> list[dict[str, Any]]:
        """Lista todos os documentos no banco (aprovados, avisos, rejeitados).

        Returns:
            Lista de dicts com {id, fabricante, modelo, tipo, status, n_chunks, source_path, indexado_em}.
        """
        if self._pool is None:
            raise RuntimeError("Pool PostgreSQL nao inicializado.")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, fabricante, modelo, tipo, status_validacao,
                       n_chunks, source_path, indexado_em
                FROM documentos_conhecimento
                ORDER BY indexado_em DESC
            """)

        return [
            {
                "id": str(row["id"]),
                "fabricante": row["fabricante"],
                "modelo": row["modelo"],
                "tipo": row["tipo"],
                "status": row["status_validacao"],
                "n_chunks": row["n_chunks"],
                "source_path": row["source_path"],
                "indexado_em": row["indexado_em"].isoformat() if row["indexado_em"] else None,
            }
            for row in rows
        ]

    async def remover_documento(self, doc_id: str) -> bool:
        """Remove um documento e seus chunks do banco.

        Args:
            doc_id: UUID do documento (string).

        Returns:
            True se o documento foi removido, False se nao encontrado.
        """
        if self._pool is None:
            raise RuntimeError("Pool PostgreSQL nao inicializado.")

        import uuid as _uuid

        try:
            uid = _uuid.UUID(doc_id)
        except ValueError:
            raise ValueError(f"ID invalido: {doc_id!r}")

        async with self._pool.acquire() as conn:
            # Remove chunks primeiro (FK)
            result = await conn.execute(
                "DELETE FROM chunks WHERE documento_id = $1",
                uid,
            )
            # Remove documento
            result = await conn.execute(
                "DELETE FROM documentos_conhecimento WHERE id = $1",
                uid,
            )
            removido = result != "DELETE 0"
            if removido:
                logger.info("documento %s removido", doc_id)
            else:
                logger.warning("documento %s nao encontrado para remocao", doc_id)
            return removido

    async def listar_chunks_ativos(self) -> list[dict[str, Any]]:
        """Lista todos os chunks de documentos aprovados para reload no FAISS.

        Returns:
            Lista de dicts com {chunk_id, texto, vetor, fabricante, modelo, tipo, ...}
        """
        if self._pool is None:
            raise RuntimeError("Pool PostgreSQL nao inicializado.")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT c.chunk_id, c.texto, c.vetor, c.fabricante, c.modelo,
                       c.tipo, c.metadata, d.id AS documento_id
                FROM chunks c
                JOIN documentos_conhecimento d ON c.documento_id = d.id
                WHERE d.status_validacao = 'aprovado'
                ORDER BY c.fabricante, c.modelo, c.chunk_index
            """)

        return [
            {
                "chunk_id": row["chunk_id"],
                "texto": row["texto"],
                "vetor": row["vetor"],
                "fabricante": row["fabricante"],
                "modelo": row["modelo"],
                "tipo": row["tipo"],
                "metadata": row["metadata"],
                "documento_id": str(row["documento_id"]),
            }
            for row in rows
        ]


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _serialize_jsonb(obj: dict[str, Any]) -> str:
    """Serializa um dict para JSON string (asyncpg espera string para JSONB)."""
    import json
    return json.dumps(obj, ensure_ascii=False, default=str)

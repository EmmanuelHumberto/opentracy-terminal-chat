"""Cliente HTTP para sincronizar chunks do PostgreSQL com o FAISS do OpenTracy.

Le chunks ativos do banco via ``KnowledgeSyncer.listar_chunks_ativos()``,
serializa e envia para ``POST /corpus/reload`` no runtime do OpenTracy.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import httpx

from app.config import BancoConfig, CorpusConfig

logger = logging.getLogger("corpus_client")


class CorpusReloadError(Exception):
    """Erro ao recarregar o indice FAISS no OpenTracy."""


class CorpusClient:
    """Cliente HTTP que mantem o FAISS do OpenTracy sincronizado com o PG.

    Uso tipico::

        client = CorpusClient(config.banco, config.corpus)
        await client.ensure_loaded()   # no startup
        # ... depois de indexar/remover documentos ...
        await client.reload_from_pg()  # forcado

    O ``KnowledgeSyncer`` e carregado sob demanda — o cliente nao
    mantem uma pool PostgreSQL aberta permanentemente.
    """

    def __init__(self, banco_config: BancoConfig, corpus_config: CorpusConfig) -> None:
        self._banco = banco_config
        self._corpus = corpus_config
        self._reload_url = corpus_config.open_tracy_reload_url.rstrip("/")
        self._timeout = corpus_config.reload_timeout
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(corpus_config.reload_timeout),
        )

    # ------------------------------------------------------------------ #
    # API publica
    # ------------------------------------------------------------------ #

    async def ensure_loaded(self) -> dict[str, Any]:
        """Carrega todos os chunks ativos do PG no FAISS do OpenTracy.

        Deve ser chamado no startup do chat. Se o FAISS ja estiver
        populado (ex.: reload previo), o endpoint substitui o indice
        atomicamente.

        Returns:
            ``{"loaded": N, "dimension": D}``.
        """
        return await self.reload_from_pg()

    async def reload_from_pg(self) -> dict[str, Any]:
        """Forca reload completo do FAISS a partir dos chunks no PG.

        Abre uma conexao temporaria com o banco, le todos os chunks
        de documentos aprovados, serializa e envia para o OpenTracy.

        Returns:
            ``{"loaded": N, "dimension": D}``.
        """
        from app.knowledge_syncer import KnowledgeSyncer

        syncer = KnowledgeSyncer(self._banco, self._corpus)
        try:
            await syncer.conectar()
            chunks_raw = await syncer.listar_chunks_ativos()
        finally:
            await syncer.desconectar()

        return await self._post_reload(chunks_raw)

    async def close(self) -> None:
        """Libera recursos HTTP."""
        await self._http.aclose()

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    async def _post_reload(self, chunks_raw: list[dict[str, Any]]) -> dict[str, Any]:
        """Converte chunks brutos do PG no formato esperado pelo endpoint
        e envia ``POST /corpus/reload``."""

        # Monta payload: cada chunk vira uma entrada no manifest + vetor
        manifest: list[dict[str, Any]] = []
        vectors: list[list[float]] = []

        for i, row in enumerate(chunks_raw):
            chunk_id = row.get("chunk_id", f"c_{i}")
            texto = row.get("texto", "")
            vetor = row.get("vetor")
            fabricante = row.get("fabricante", "")
            modelo = row.get("modelo", "")
            tipo = row.get("tipo", "")
            metadata = row.get("metadata", {})
            doc_id = row.get("documento_id", "")

            if vetor is None:
                logger.warning("chunk %s sem vetor — pulando", chunk_id)
                continue

            # Converte para lista de floats (pode vir como string do JSONB)
            if isinstance(vetor, str):
                import json
                vetor = json.loads(vetor)
            vetor = [float(v) for v in vetor]

            manifest.append({
                "id": chunk_id,
                "text": texto,
                "source": f"{fabricante}/{modelo}" if fabricante and modelo else doc_id,
                "chunk_index": i,
                "n_chunks": len(chunks_raw),
                "metadata": {
                    "fabricante": fabricante,
                    "modelo": modelo,
                    "tipo": tipo,
                    "documento_id": doc_id,
                    **(metadata if isinstance(metadata, dict) else {}),
                },
            })
            vectors.append(vetor)

        if not manifest:
            logger.info("nenhum chunk ativo — enviando reload vazio")
            payload = {"chunks": [], "vectors": []}
        else:
            payload = {"chunks": manifest, "vectors": vectors}

        logger.info("enviando %d chunks (dim=%d) para %s",
                     len(manifest),
                     len(vectors[0]) if vectors else 0,
                     self._reload_url)

        try:
            resp = await self._http.post(
                self._reload_url,
                json=payload,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                detail = exc.response.json().get("detail", "")
            except Exception:
                detail = exc.response.text[:200]
            raise CorpusReloadError(
                f"OpenTracy retornou HTTP {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise CorpusReloadError(
                f"Falha de conexao com OpenTracy em {self._reload_url}: {exc}"
            ) from exc

        result = resp.json()
        logger.info("FAISS recarregado: %d chunks, dim=%d",
                     result.get("loaded", 0),
                     result.get("dimension", 0))
        return result

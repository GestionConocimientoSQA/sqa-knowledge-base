"""Adapter `EmbedderPort` → Cohere SDK directo.

Implementa la interfaz `sqa_kb.ports.gateways.EmbedderPort` usando el
SDK oficial `cohere` (AsyncClientV2). Es el default en dev local y prod
mientras TI no requiera self-hosting (BGE-M3 alternativa futura).

Decisiones de diseño:
- **Async-first**: `AsyncClientV2`, no se mezcla sync.
- **input_type distinto al indexar vs buscar**: Cohere usa el mismo modelo
  pero la calidad del retrieval mejora con `search_document` en indexación
  y `search_query` en búsqueda (ROADMAP §17.3).
- **Batching**: Cohere acepta hasta 96 textos por request. El indexer
  (Fase 3.2) divide listas más largas. Acá NO lo dividimos — fail fast
  si el caller manda > 96 (le pasamos el control de batching para no
  esconder costos).
- **Sin reintentos manuales**: el SDK ya hace exponential backoff con
  `max_retries` por default.
- **Cliente inyectable** para tests sin HTTP (mismo patrón que el adapter
  Anthropic de Fase 2.0).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from cohere import AsyncClientV2

from sqa_kb.adapters.embeddings.pricing import estimate_embed_cost_usd
from sqa_kb.ports.gateways import EmbeddingBatch

logger = logging.getLogger(__name__)


# Cohere acepta hasta 96 textos por request (ROADMAP §17.3).
MAX_BATCH_SIZE: int = 96


class CohereEmbedder:
    """`EmbedderPort` concreto que habla directo con `api.cohere.com`.

    `client` opcional para inyectar mocks en tests sin parchar el módulo.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "embed-multilingual-v3.0",
        client: AsyncClientV2 | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client or AsyncClientV2(api_key=api_key)

    # ===========================================================================
    # embed_documents (indexación)
    # ===========================================================================

    async def embed_documents(self, texts: Sequence[str]) -> EmbeddingBatch:
        """Embedea una lista de chunks a indexar.

        El caller (`rag/indexer.py`) debe dividir en grupos de hasta
        `MAX_BATCH_SIZE` antes de llamar a este método — fail fast si
        recibe más, para que el costo del request se mantenga visible.
        """
        if not texts:
            raise ValueError("texts vacía — el embedder necesita al menos 1 texto")
        if len(texts) > MAX_BATCH_SIZE:
            raise ValueError(
                f"batch demasiado grande: {len(texts)} > {MAX_BATCH_SIZE}. "
                "El indexer debe dividir en sub-batches."
            )

        response = await self._client.embed(
            model=self._model,
            input_type="search_document",
            texts=list(texts),
            embedding_types=["float"],
        )
        return self._build_batch(response)

    # ===========================================================================
    # embed_query (búsqueda)
    # ===========================================================================

    async def embed_query(self, text: str) -> EmbeddingBatch:
        """Embedea una consulta única. `input_type=search_query` para
        priorizar recall en el retrieval (ROADMAP §17.3)."""
        if not text.strip():
            raise ValueError("text vacío — el embedder necesita contenido")

        response = await self._client.embed(
            model=self._model,
            input_type="search_query",
            texts=[text],
            embedding_types=["float"],
        )
        return self._build_batch(response)

    # ===========================================================================
    # Helpers internos
    # ===========================================================================

    def _build_batch(self, response: Any) -> EmbeddingBatch:
        """Convierte la respuesta del SDK a nuestro `EmbeddingBatch`.

        Cohere V2 devuelve `EmbedByTypeResponse` con `embeddings.float` y
        `meta.billed_units.input_tokens`. Si la forma cambia entre
        versiones del SDK, este método es el único punto a tocar.
        """
        vectors_raw = getattr(response.embeddings, "float", None) or []
        vectors = tuple(tuple(float(v) for v in row) for row in vectors_raw)
        billed = getattr(response, "meta", None)
        input_tokens = 0
        if billed is not None:
            units = getattr(billed, "billed_units", None)
            if units is not None:
                input_tokens = getattr(units, "input_tokens", 0) or 0
        cost = estimate_embed_cost_usd(model=self._model, input_tokens=input_tokens)
        return EmbeddingBatch(
            vectors=vectors,
            input_tokens=input_tokens,
            cost_usd=cost,
            model=self._model,
        )

"""Adapters de `EmbedderPort` (Fase 3 — RAG vectorial).

Implementaciones:
- `cohere.CohereEmbedder` — Cohere embed-multilingual-v3.0 (default).
- Plan futuro: BgeM3Embedder self-hosted vía text-embeddings-inference,
  si TI decide no salir de Azure con embeddings (mismo schema 1024 dims).

El swap se controla con `settings.embedder_kind` y se cablea en `main.py`.
"""

from sqa_kb.adapters.embeddings.cohere import CohereEmbedder
from sqa_kb.adapters.embeddings.pricing import (
    COHERE_MODEL_PRICING,
    estimate_embed_cost_usd,
)

__all__ = [
    "COHERE_MODEL_PRICING",
    "CohereEmbedder",
    "estimate_embed_cost_usd",
]

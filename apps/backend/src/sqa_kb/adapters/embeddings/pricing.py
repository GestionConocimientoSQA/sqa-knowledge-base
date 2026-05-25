"""Tabla de precios de modelos de embeddings + helper de estimación.

Separamos pricing del adapter (mismo patrón que `adapters/llm/pricing.py`)
para:
- Cambia con más frecuencia que la integración HTTP (Cohere ajusta tarifas).
- El indexer (Fase 3.2) lo importa sin acoplarse al SDK.
- Tests aislados.

Precios en USD por **millón de tokens** (espejo de cómo Cohere los publica).

Fuente: https://cohere.com/pricing (revisar trimestralmente).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CohereEmbedPricing:
    """Tarifa Cohere por millón de tokens (mismo precio para
    `search_document` y `search_query`)."""

    per_mtok_usd: float


# Precios revisados 2026-05. Si Cohere actualiza, este dict es el único
# lugar a tocar.
COHERE_MODEL_PRICING: dict[str, CohereEmbedPricing] = {
    "embed-multilingual-v3.0": CohereEmbedPricing(per_mtok_usd=0.10),
    "embed-english-v3.0": CohereEmbedPricing(per_mtok_usd=0.10),
    # Light tiene mitad de dimensiones (384) — solo si TI pide cortar costo.
    "embed-multilingual-light-v3.0": CohereEmbedPricing(per_mtok_usd=0.02),
}


def estimate_embed_cost_usd(*, model: str, input_tokens: int) -> float:
    """Calcula el costo en USD de una invocación al embedder.

    Modelo desconocido → `0.0` (no rompe el grafo si Cohere suelta uno
    nuevo). El caller decide si loggear warning.
    """
    pricing = COHERE_MODEL_PRICING.get(model)
    if pricing is None:
        return 0.0
    return (input_tokens * pricing.per_mtok_usd) / 1_000_000

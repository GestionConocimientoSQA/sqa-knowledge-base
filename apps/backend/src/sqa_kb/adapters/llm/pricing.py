"""Tabla de precios de modelos Anthropic + helper de estimación.

Separamos pricing del adapter porque:
- Cambia con más frecuencia que la integración HTTP (Anthropic ajusta tarifas).
- El cost tracker (Fase 2.2) puede importarlo sin acoplarse al SDK.
- Se prueba de forma aislada.

Precios en USD por **millón de tokens** (matchea la forma en que Anthropic
los publica). El helper `estimate_cost_usd` convierte a tokens absolutos.

Fuente: https://www.anthropic.com/pricing (revisar trimestralmente).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """Tarifa por millón de tokens. `cache_*` aplica solo si se usa prompt
    caching (Fase 2.2 — los skills + system prompts son ideales para esto).
    """

    input_per_mtok: float
    output_per_mtok: float
    cache_write_per_mtok: float
    """5-min cache write — el primer hit del bloque cacheable."""
    cache_read_per_mtok: float
    """Lectura desde caché — barato y rápido."""


# ===========================================================================
# Catálogo (precios revisados 2026-05). Si Anthropic actualiza tarifas, este
# dict es el único lugar a tocar. Los unit tests cubren que el helper de
# costo respete la fórmula.
# ===========================================================================

MODEL_PRICING: dict[str, ModelPricing] = {
    "claude-sonnet-4-5": ModelPricing(
        input_per_mtok=3.0,
        output_per_mtok=15.0,
        cache_write_per_mtok=3.75,
        cache_read_per_mtok=0.30,
    ),
    "claude-haiku-4-5": ModelPricing(
        input_per_mtok=1.0,
        output_per_mtok=5.0,
        cache_write_per_mtok=1.25,
        cache_read_per_mtok=0.10,
    ),
    "claude-opus-4-5": ModelPricing(
        input_per_mtok=15.0,
        output_per_mtok=75.0,
        cache_write_per_mtok=18.75,
        cache_read_per_mtok=1.50,
    ),
}


def estimate_cost_usd(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_write_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> float:
    """Calcula el costo en USD de una invocación al LLM.

    `input_tokens` es solo el input fresco (NO incluye `cache_*`). Anthropic
    los reporta separados — los `usage` campos de cada respuesta vienen
    desglosados (`input_tokens`, `cache_creation_input_tokens`,
    `cache_read_input_tokens`).

    Si el modelo no está en `MODEL_PRICING`, devolvemos `0.0` y dejamos que
    el caller decida (loggear warning, fallar, etc.). No fallamos acá para
    no romper el grafo del agente cuando Anthropic suelte un modelo nuevo.
    """
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        return 0.0
    per_mtok = 1_000_000
    return (
        input_tokens * pricing.input_per_mtok
        + output_tokens * pricing.output_per_mtok
        + cache_write_tokens * pricing.cache_write_per_mtok
        + cache_read_tokens * pricing.cache_read_per_mtok
    ) / per_mtok

"""Adapters de `LlmGateway` (Fase 2).

Implementaciones disponibles:
- `anthropic_direct.AnthropicDirectGateway` — `anthropic` SDK con API key
  personal. Default en dev local.
- `litellm.LitellmGateway` — Fase 1B-azure, si TI provee proxy gestionado.

El swap se controla con `settings.llm_gateway_kind` y se cablea en `main.py`.
"""

from sqa_kb.adapters.llm.anthropic_direct import AnthropicDirectGateway
from sqa_kb.adapters.llm.pricing import MODEL_PRICING, ModelPricing, estimate_cost_usd

__all__ = [
    "AnthropicDirectGateway",
    "MODEL_PRICING",
    "ModelPricing",
    "estimate_cost_usd",
]

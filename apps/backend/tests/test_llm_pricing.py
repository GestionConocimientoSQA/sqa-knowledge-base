"""Tests de la tabla de pricing + helper de costo."""

from __future__ import annotations

import pytest

from sqa_kb.adapters.llm.pricing import MODEL_PRICING, estimate_cost_usd


def test_pricing_table_includes_default_models() -> None:
    """Los 3 modelos por default de config tienen entrada de precio."""
    assert "claude-sonnet-4-5" in MODEL_PRICING
    assert "claude-haiku-4-5" in MODEL_PRICING
    assert "claude-opus-4-5" in MODEL_PRICING


def test_pricing_sonnet_input_cheaper_than_output() -> None:
    """Sanity check: output tokens son siempre más caros que input."""
    for model, p in MODEL_PRICING.items():
        assert p.output_per_mtok > p.input_per_mtok, (
            f"{model}: output debería ser más caro que input"
        )


def test_pricing_cache_read_is_discount() -> None:
    """Cache read debe ser sustancialmente más barato que input fresco."""
    for model, p in MODEL_PRICING.items():
        assert p.cache_read_per_mtok < p.input_per_mtok / 2, (
            f"{model}: cache_read debe ser <50% del input"
        )


def test_estimate_cost_simple_input_output() -> None:
    """Sonnet 4.5: 1k input + 1k output = (3 + 15) / 1000 = 0.018 USD."""
    cost = estimate_cost_usd(
        model="claude-sonnet-4-5",
        input_tokens=1000,
        output_tokens=1000,
    )
    assert cost == pytest.approx(0.018, rel=1e-6)


def test_estimate_cost_includes_cache_components() -> None:
    """Si hay cache_write + cache_read los suma con su tarifa propia."""
    cost = estimate_cost_usd(
        model="claude-sonnet-4-5",
        input_tokens=100,
        output_tokens=200,
        cache_write_tokens=500,
        cache_read_tokens=1000,
    )
    # 100*3 + 200*15 + 500*3.75 + 1000*0.30 = 300 + 3000 + 1875 + 300 = 5475
    # / 1_000_000 = 0.005475
    assert cost == pytest.approx(0.005475, rel=1e-6)


def test_estimate_cost_unknown_model_returns_zero() -> None:
    """Modelo desconocido: 0.0 sin lanzar excepción. Permite que un modelo
    nuevo de Anthropic no rompa el grafo del agente."""
    cost = estimate_cost_usd(
        model="claude-superpro-99",
        input_tokens=1000,
        output_tokens=1000,
    )
    assert cost == 0.0


def test_estimate_cost_zero_tokens() -> None:
    """Sin tokens, costo cero — caso edge para errores de upstream."""
    cost = estimate_cost_usd(
        model="claude-sonnet-4-5",
        input_tokens=0,
        output_tokens=0,
    )
    assert cost == 0.0

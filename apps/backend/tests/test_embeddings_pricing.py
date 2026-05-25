"""Tests de la tabla de pricing Cohere + helper de costo."""

from __future__ import annotations

import pytest

from sqa_kb.adapters.embeddings.pricing import (
    COHERE_MODEL_PRICING,
    estimate_embed_cost_usd,
)


def test_pricing_includes_default_model() -> None:
    """El modelo default de ROADMAP §17.1 está en la tabla."""
    assert "embed-multilingual-v3.0" in COHERE_MODEL_PRICING
    assert "embed-multilingual-light-v3.0" in COHERE_MODEL_PRICING


def test_pricing_multilingual_v3_costs_usd_010_per_mtok() -> None:
    pricing = COHERE_MODEL_PRICING["embed-multilingual-v3.0"]
    assert pricing.per_mtok_usd == 0.10


def test_pricing_light_is_cheaper_than_full() -> None:
    """Sanity: el modelo light cuesta menos que el full."""
    light = COHERE_MODEL_PRICING["embed-multilingual-light-v3.0"]
    full = COHERE_MODEL_PRICING["embed-multilingual-v3.0"]
    assert light.per_mtok_usd < full.per_mtok_usd


def test_estimate_cost_simple() -> None:
    """1M tokens en v3.0 = USD 0.10."""
    cost = estimate_embed_cost_usd(
        model="embed-multilingual-v3.0", input_tokens=1_000_000
    )
    assert cost == pytest.approx(0.10, rel=1e-6)


def test_estimate_cost_partial_million() -> None:
    """100k tokens en v3.0 = USD 0.01."""
    cost = estimate_embed_cost_usd(
        model="embed-multilingual-v3.0", input_tokens=100_000
    )
    assert cost == pytest.approx(0.01, rel=1e-6)


def test_estimate_cost_unknown_model_returns_zero() -> None:
    """Modelo desconocido → 0 (no rompe pipeline si Cohere suelta modelo nuevo)."""
    cost = estimate_embed_cost_usd(
        model="cohere-superembed-99", input_tokens=1_000_000
    )
    assert cost == 0.0


def test_estimate_cost_zero_tokens() -> None:
    cost = estimate_embed_cost_usd(
        model="embed-multilingual-v3.0", input_tokens=0
    )
    assert cost == 0.0


def test_estimate_cost_handles_very_large_token_counts() -> None:
    """100M tokens (~equivalente a indexar el KB inicial completo varias veces)."""
    cost = estimate_embed_cost_usd(
        model="embed-multilingual-v3.0", input_tokens=100_000_000
    )
    assert cost == pytest.approx(10.0, rel=1e-6)

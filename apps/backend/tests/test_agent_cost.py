"""Tests del cost tracker funcional.

Cubre:
- `accumulate` suma deltas a los totales del state.
- `CostDelta` valida no-negatividad de tokens y costo.
- Acumulación múltiple es asociativa.
- Precisión: el round a 6 decimales aplica.
- `budget_status` clasifica ok/warn/hard según umbrales.
- Boundaries: igualdad exacta con el umbral cuenta como cruzado.
- Inversión de umbrales (warn >= hard) lanza ValueError.
"""

from __future__ import annotations

import pytest

from sqa_kb.agent.cost import (
    DEFAULT_HARD_LIMIT_USD,
    DEFAULT_WARN_AT_USD,
    BudgetStatus,
    CostDelta,
    accumulate,
    budget_status,
)
from sqa_kb.agent.state import initial_state


def _fresh_state(**overrides: object):  # type: ignore[no-untyped-def]
    state = initial_state(
        session_id="s", user_id="o", user_name="n", mode="capture"
    )
    for k, v in overrides.items():
        setattr(state, k, v)
    return state


# ===========================================================================
# CostDelta validation
# ===========================================================================


def test_cost_delta_accepts_valid_input() -> None:
    d = CostDelta(input_tokens=10, output_tokens=5, cost_usd=0.0001)
    assert d.input_tokens == 10
    assert d.cost_usd == 0.0001


def test_cost_delta_rejects_negative_input_tokens() -> None:
    with pytest.raises(ValueError, match="tokens"):
        CostDelta(input_tokens=-1, output_tokens=0, cost_usd=0.0)


def test_cost_delta_rejects_negative_output_tokens() -> None:
    with pytest.raises(ValueError, match="tokens"):
        CostDelta(input_tokens=0, output_tokens=-1, cost_usd=0.0)


def test_cost_delta_rejects_negative_cost() -> None:
    with pytest.raises(ValueError, match="cost_usd"):
        CostDelta(input_tokens=0, output_tokens=0, cost_usd=-0.01)


def test_cost_delta_zero_is_valid() -> None:
    """Edge: un mensaje que no consumió tokens (error temprano)."""
    d = CostDelta(input_tokens=0, output_tokens=0, cost_usd=0.0)
    assert d.cost_usd == 0.0


# ===========================================================================
# accumulate
# ===========================================================================


def test_accumulate_adds_delta_to_state_totals() -> None:
    state = _fresh_state()
    delta = CostDelta(input_tokens=100, output_tokens=50, cost_usd=0.00125)
    update = accumulate(state, delta)
    assert update == {
        "total_input_tokens": 100,
        "total_output_tokens": 50,
        "total_cost_usd": 0.00125,
    }


def test_accumulate_builds_on_existing_totals() -> None:
    state = _fresh_state(
        total_input_tokens=200,
        total_output_tokens=80,
        total_cost_usd=0.005,
    )
    delta = CostDelta(input_tokens=50, output_tokens=20, cost_usd=0.0006)
    update = accumulate(state, delta)
    assert update["total_input_tokens"] == 250
    assert update["total_output_tokens"] == 100
    assert update["total_cost_usd"] == pytest.approx(0.0056, rel=1e-6)


def test_accumulate_associativity() -> None:
    """Aplicar A→B debe dar lo mismo que aplicar B→A (suma conmutativa)."""
    s0 = _fresh_state()
    d1 = CostDelta(input_tokens=10, output_tokens=5, cost_usd=0.001)
    d2 = CostDelta(input_tokens=20, output_tokens=15, cost_usd=0.002)

    # path 1: s0 + d1 + d2
    u1 = accumulate(s0, d1)
    s1 = s0.model_copy(update=u1)
    u_final_1 = accumulate(s1, d2)

    # path 2: s0 + d2 + d1
    u2 = accumulate(s0, d2)
    s2 = s0.model_copy(update=u2)
    u_final_2 = accumulate(s2, d1)

    assert u_final_1 == u_final_2


def test_accumulate_rounds_to_six_decimals() -> None:
    """Float arithmetic puede producir 0.000000003 — redondeamos para que
    el dashboard no muestre 12 decimales."""
    state = _fresh_state(total_cost_usd=0.0001)
    delta = CostDelta(input_tokens=1, output_tokens=1, cost_usd=0.0000001)
    update = accumulate(state, delta)
    # 0.0001 + 0.0000001 = 0.0001001 — redondeado a 6 decimales = 0.0001
    assert update["total_cost_usd"] == 0.0001


# ===========================================================================
# budget_status
# ===========================================================================


def test_budget_status_ok_when_below_warn() -> None:
    state = _fresh_state(total_cost_usd=0.10)
    status = budget_status(state)
    assert status.level == "ok"
    assert status.is_warn is False
    assert status.is_hard is False


def test_budget_status_warn_when_above_warn_below_hard() -> None:
    state = _fresh_state(total_cost_usd=DEFAULT_WARN_AT_USD + 0.01)
    status = budget_status(state)
    assert status.level == "warn"
    assert status.is_warn is True
    assert status.is_hard is False


def test_budget_status_hard_when_above_hard_limit() -> None:
    state = _fresh_state(total_cost_usd=DEFAULT_HARD_LIMIT_USD + 1.0)
    status = budget_status(state)
    assert status.level == "hard"
    assert status.is_warn is True
    assert status.is_hard is True


def test_budget_status_boundary_at_warn_counts_as_warn() -> None:
    """Igualdad exacta con el umbral se considera cruzado."""
    state = _fresh_state(total_cost_usd=DEFAULT_WARN_AT_USD)
    status = budget_status(state)
    assert status.level == "warn"


def test_budget_status_boundary_at_hard_counts_as_hard() -> None:
    state = _fresh_state(total_cost_usd=DEFAULT_HARD_LIMIT_USD)
    status = budget_status(state)
    assert status.level == "hard"


def test_budget_status_custom_thresholds() -> None:
    state = _fresh_state(total_cost_usd=0.05)
    status = budget_status(state, warn_at_usd=0.02, hard_limit_usd=0.10)
    assert status.level == "warn"  # 0.05 está entre 0.02 y 0.10


def test_budget_status_rejects_inverted_thresholds() -> None:
    state = _fresh_state(total_cost_usd=0.0)
    with pytest.raises(ValueError, match="warn_at"):
        budget_status(state, warn_at_usd=0.5, hard_limit_usd=0.2)


def test_budget_status_rejects_equal_thresholds() -> None:
    state = _fresh_state(total_cost_usd=0.0)
    with pytest.raises(ValueError, match="warn_at"):
        budget_status(state, warn_at_usd=0.5, hard_limit_usd=0.5)


def test_budget_status_zero_used() -> None:
    state = _fresh_state(total_cost_usd=0.0)
    status = budget_status(state)
    assert status.level == "ok"
    assert status.used_usd == 0.0


def test_budget_status_dataclass_immutable() -> None:
    state = _fresh_state(total_cost_usd=0.1)
    status = budget_status(state)
    with pytest.raises((AttributeError, Exception)):
        status.level = "hard"  # type: ignore[misc] — frozen


# ===========================================================================
# BudgetStatus direct construction edge
# ===========================================================================


def test_budget_status_dataclass_construct_directly() -> None:
    """Sanity: la dataclass es frozen pero permite construir directo."""
    s = BudgetStatus(
        level="ok", used_usd=0.0, warn_at_usd=0.5, hard_limit_usd=5.0
    )
    assert s.level == "ok"
    assert s.is_warn is False

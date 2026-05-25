"""Cost tracker del agente — Fase 2.2.

Diseño funcional puro: los totales viven en `AgentState.total_*`. El
checkpointer ya persiste el state turno a turno, así que no necesitamos
una tabla aparte ni un servicio con estado mutable.

Este módulo expone:
- `accumulate(...)`: dado un state y los tokens/costo de un mensaje,
  devuelve un *partial state update* compatible con LangGraph.
- `budget_warning(...)`: helper que indica si una sesión está pasada de
  un umbral (Fase 12 lo conectará a notificaciones; ahora se loggea).

Mantenemos esto SIN clase con estado:
- LangGraph nodes ya son funcionales (reciben state, retornan dict).
- Una clase singleton acoplaría tests a teardown manual.
- El "tracker" agregado por usuario/global lo hace una query sobre
  `messages.token_usage` cuando Fase 9 admin lo necesite — no es
  responsabilidad del agente en runtime.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqa_kb.agent.state import AgentState

# Umbrales por sesión. Si una sesión supera el límite mostramos warning
# en logs (Fase 12 lo conecta a UI / Slack). Conservadores en dev local
# donde la key personal del usuario tiene presupuesto chico.
DEFAULT_WARN_AT_USD: float = 0.50
"""Cuando una sesión cruza esto, loggear `warning`."""

DEFAULT_HARD_LIMIT_USD: float = 5.00
"""Cuando una sesión cruza esto, los nodos deberían rechazar nuevos
turnos. La política de qué hacer la decide el orquestador (Fase 2.6)."""


@dataclass(frozen=True, slots=True)
class CostDelta:
    """Lo que aportó UNA invocación al LLM. Es lo que el adapter emite
    en su evento `stop` o lo que devuelve `complete()`."""

    input_tokens: int
    output_tokens: int
    cost_usd: float

    def __post_init__(self) -> None:
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise ValueError("tokens no pueden ser negativos")
        if self.cost_usd < 0:
            raise ValueError("cost_usd no puede ser negativo")


def accumulate(state: AgentState, delta: CostDelta) -> dict[str, int | float]:
    """Suma el `delta` a los totales del state. Devuelve un partial dict
    que LangGraph fusiona con el state actual.

    Forma del retorno matchea las keys de `AgentState` para que el nodo
    pueda hacer `return {**accumulate(state, delta), ...otras keys}`.
    """
    return {
        "total_input_tokens": state.total_input_tokens + delta.input_tokens,
        "total_output_tokens": state.total_output_tokens + delta.output_tokens,
        "total_cost_usd": round(state.total_cost_usd + delta.cost_usd, 6),
    }


@dataclass(frozen=True, slots=True)
class BudgetStatus:
    """Resultado de `budget_warning`. `level` es uno de `ok`, `warn`, `hard`."""

    level: str
    """`ok` < warn_at < `warn` < hard_limit < `hard`."""
    used_usd: float
    warn_at_usd: float
    hard_limit_usd: float

    @property
    def is_warn(self) -> bool:
        return self.level in ("warn", "hard")

    @property
    def is_hard(self) -> bool:
        return self.level == "hard"


def budget_status(
    state: AgentState,
    *,
    warn_at_usd: float = DEFAULT_WARN_AT_USD,
    hard_limit_usd: float = DEFAULT_HARD_LIMIT_USD,
) -> BudgetStatus:
    """Clasifica el uso actual en ok/warn/hard según umbrales.

    `warn_at` debe ser estrictamente menor que `hard_limit`, sino lanzamos
    `ValueError` — silenciar la inversión sería un bug silencioso peor.
    """
    if warn_at_usd >= hard_limit_usd:
        raise ValueError(
            f"warn_at ({warn_at_usd}) debe ser < hard_limit ({hard_limit_usd})"
        )
    used = state.total_cost_usd
    if used >= hard_limit_usd:
        level = "hard"
    elif used >= warn_at_usd:
        level = "warn"
    else:
        level = "ok"
    return BudgetStatus(
        level=level,
        used_usd=used,
        warn_at_usd=warn_at_usd,
        hard_limit_usd=hard_limit_usd,
    )

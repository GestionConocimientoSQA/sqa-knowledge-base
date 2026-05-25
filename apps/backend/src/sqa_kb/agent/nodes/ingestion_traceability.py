"""Nodo ingestion_traceability (modo C — segundo paso).

Doble responsabilidad por turno:
1. Primera entrada (vía Command desde ingestion_classify): emite prompt
   pidiendo metadata de trazabilidad. Setea awaiting=ingest_meta.
2. Segunda entrada (awaiting=ingest_meta + user respondió): parsea el
   mensaje en busca de los 4 campos, popula `Traceability`, y delega a
   `index_ingestion` vía Command.

Parser heurístico: el usuario manda los 4 datos en una sola respuesta.
NO usamos LLM acá — un regex simple alcanza, y nos ahorramos costo +
latencia. Si Fase 5+ requiere parseo más estricto, ahí sumamos LLM.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from langgraph.types import Command

from sqa_kb.agent.state import AgentState, Traceability
from sqa_kb.agent.templates import render

NodeFn = Callable[[AgentState], Awaitable[dict[str, Any] | Command]]


# Regex para extraer fecha ISO en el texto.
_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
# URLs / paths para "fuente original".
_URL_RE = re.compile(
    r"(https?://\S+|sharepoint:\S+|[A-Z]:\\[\w\\.-]+|/\S+/\S+)"
)
# Versión preferentemente con prefijo `v`, `vN`, `versión N`. Las fechas
# ISO también contienen números separados por `-`, pero no por `.`, así
# que requerimos al menos un `.` para evitar matchear "2026" o "2026-05".
_VERSION_RE_PREFIXED = re.compile(
    r"v(?:ersi[oó]n)?\s*([0-9]+(?:\.[0-9]+){1,2})\b", re.IGNORECASE
)
_VERSION_RE_DOTTED = re.compile(r"\b([0-9]+(?:\.[0-9]+){1,2})\b")


def make_ingestion_traceability_node() -> NodeFn:
    """Factory del nodo de trazabilidad. Sin deps."""

    async def ingestion_traceability(
        state: AgentState,
    ) -> dict[str, Any] | Command:
        if state.awaiting_confirmation != "ingest_meta":
            return _emit_traceability_prompt(state)

        # Vuelta siguiente: parsear la respuesta y avanzar.
        user_input = _last_user_msg(state)
        if not user_input:
            return _ask_again(state)

        traceability = _parse_traceability(user_input)
        ack = (
            f"Anoté la trazabilidad (aprobador: **{traceability.approved_by}**, "
            f"fecha: **{traceability.approval_date}**). Indexando el "
            f"documento ahora."
        )
        message = _agent_message(state, content=ack, stage="capture_traceability")
        return Command(
            goto="index_ingestion",
            update={
                "messages": [message],
                "traceability": traceability,
                "current_stage": "capture_traceability",
                "previous_stage": state.current_stage,
                "needs_user_input": False,
                "awaiting_confirmation": None,
            },
        )

    return ingestion_traceability


# ===========================================================================
# Helpers
# ===========================================================================


def _emit_traceability_prompt(state: AgentState) -> dict[str, Any]:
    if state.suggested_classification is None:
        # Defensa: llegamos sin clasificación. No deberíamos.
        return {
            "messages": [
                _agent_message(
                    state,
                    content="Necesito clasificar el documento antes de pedirte trazabilidad.",
                    stage="capture_traceability",
                )
            ],
            "current_stage": "capture_traceability",
            "previous_stage": state.current_stage,
            "needs_user_input": True,
            "awaiting_confirmation": "error",
            "last_error": "missing_classification",
        }

    text = render(
        "ingestion_traceability_prompt.j2",
        classification=state.suggested_classification.model_dump(),
    )
    message = _agent_message(state, content=text, stage="capture_traceability")
    return {
        "messages": [message],
        "current_stage": "capture_traceability",
        "previous_stage": state.current_stage,
        "needs_user_input": True,
        "awaiting_confirmation": "ingest_meta",
    }


def _ask_again(state: AgentState) -> dict[str, Any]:
    text = "Necesito los datos de trazabilidad — aprobador, fecha, fuente."
    message = _agent_message(state, content=text, stage="capture_traceability")
    return {
        "messages": [message],
        "current_stage": "capture_traceability",
        "previous_stage": state.current_stage,
        "needs_user_input": True,
        "awaiting_confirmation": "ingest_meta",
    }


def _parse_traceability(user_input: str) -> Traceability:
    """Extrae los 4 campos del texto libre del usuario.

    - `approved_by`: la primera línea no vacía (heurística — el usuario
      suele empezar con el nombre/rol).
    - `approval_date`: primer match de YYYY-MM-DD.
    - `source_origin`: primer URL/path/sharepoint match, o "no especificado".
    - `source_version`: primer match de patrón vN.M.K o N.M (opcional).
    """
    lines = [ln.strip() for ln in user_input.splitlines() if ln.strip()]
    approved_by = _extract_approved_by(lines)

    date_match = _DATE_RE.search(user_input)
    approval_date = (
        date_match.group(1) if date_match else datetime.now(UTC).date().isoformat()
    )

    url_match = _URL_RE.search(user_input)
    source_origin = url_match.group(0) if url_match else "no especificado"

    # Buscamos primero versiones con prefijo explícito (v1.0, versión 1.2);
    # si no hay, caemos a un número con punto (1.2 / 1.2.3) — nunca matchea
    # fechas ISO porque exigimos al menos un `.`.
    version_match = _VERSION_RE_PREFIXED.search(user_input)
    if version_match is None:
        version_match = _VERSION_RE_DOTTED.search(user_input)
    source_version = version_match.group(1) if version_match else None

    return Traceability(
        approved_by=approved_by,
        approval_date=approval_date,
        source_origin=source_origin,
        source_version=source_version,
    )


def _extract_approved_by(lines: list[str]) -> str:
    """Saca el nombre/rol del aprobador. Heurística simple:
    - Si hay enumeración tipo `1. nombre`, usa el contenido sin el número.
    - Sino, usa la primera línea no vacía.
    - Si la línea pega una URL al final, la corta.
    """
    if not lines:
        return "no especificado"
    first = lines[0]
    # Saca prefijos tipo "1.", "1)", "- ", "* ".
    cleaned = re.sub(r"^[\d\.\)\-\*\s]+", "", first).strip()
    # Si tiene URL pegada al final, la corta.
    url_match = _URL_RE.search(cleaned)
    if url_match:
        cleaned = cleaned[: url_match.start()].strip().rstrip(":,-")
    return cleaned or "no especificado"


def _last_user_msg(state: AgentState) -> str:
    for msg in reversed(state.messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                return content.strip()
    return ""


def _agent_message(
    state: AgentState, *, content: str, stage: str
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": f"msg-it-{state.session_id}-{len(state.messages)}",
        "role": "agent",
        "content": content,
        "stage": stage,
        "status": "complete",
        "started_at": now,
        "ended_at": now,
    }

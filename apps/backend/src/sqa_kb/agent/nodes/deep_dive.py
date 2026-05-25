"""Nodo deep_dive (ETAPA 3).

Banco de preguntas dirigidas por tipo de documento. Si el tipo no tiene
preguntas pre-armadas, degrada a una pregunta genérica.

Doble responsabilidad por turno (mismo patrón que free_capture):
1. Primera entrada → emite las preguntas y espera respuestas.
2. Segunda entrada → guarda las respuestas en `deep_dive_qa` y avanza a
   ETAPA 4 (validation_summary).

Para 2.4 simplificamos:
- Una sola tanda de preguntas (no iteraciones).
- Las respuestas del usuario se guardan como un único bloque bajo
  una key consolidada por tipo.

Las preguntas vienen de `QUESTIONS_BY_TYPE` — banco curado del equipo
SQA, editable acá (Fase 9 admin lo expone como skill si queremos
gobernarlo por GK Lead sin redeploy).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from langgraph.types import Command

from sqa_kb.agent.state import AgentState
from sqa_kb.agent.templates import render

NodeFn = Callable[[AgentState], Awaitable[dict[str, Any] | Command]]


# Banco de preguntas por tipo. Mantenemos uno por línea para que el diff
# de cambios sea claro.
QUESTIONS_BY_TYPE: dict[str, list[str]] = {
    "POL": [
        "¿Cuál es el alcance de esta política (qué cubre y qué NO)?",
        "¿Quién es el responsable de hacerla cumplir?",
        "¿Hay excepciones contempladas?",
    ],
    "PROC": [
        "¿Qué disparador inicia este procedimiento?",
        "¿Cuáles son los pasos principales en orden?",
        "¿Qué pasa si un paso falla?",
    ],
    "GUIA": [
        "¿Para qué tipo de situación sirve esta guía?",
        "¿Hay un ejemplo concreto que ilustre el uso?",
    ],
    "INST": [
        "¿Cuál es el resultado esperado al ejecutar esto?",
        "¿Hay precondiciones que el usuario deba verificar?",
    ],
    "SERV": [
        "¿Qué servicio se está documentando?",
        "¿Quién es el dueño del servicio?",
        "¿Qué SLAs aplican?",
    ],
    "MTEC": [
        "¿Cuál fue el problema original?",
        "¿Qué alternativas se evaluaron?",
        "¿Qué se decidió y por qué?",
    ],
    "ACEL": [
        "¿Qué problema acelera resolver?",
        "¿Cómo se usa el acelerador (input/output)?",
        "¿Qué precauciones tomar?",
    ],
    "UEN": [
        "¿Cuál es el alcance de la unidad de negocio?",
        "¿Qué métricas la definen?",
    ],
    "ARCL": [
        "¿Qué arquetipo de cliente se describe?",
        "¿Qué necesidades típicas tiene?",
    ],
    "FORM": [
        "¿Para qué se usa este formato?",
        "¿Quién debe llenarlo y cuándo?",
    ],
    "PRES": [
        "¿Cuál es la audiencia objetivo?",
        "¿Cuál es el mensaje central?",
    ],
}


def make_deep_dive_node() -> NodeFn:
    """Factory del nodo deep_dive. Sin dependencias externas."""

    async def deep_dive(state: AgentState) -> dict[str, Any]:
        if state.classification is None:
            # Defensivo — el dispatcher no debería entrar acá sin clasificación.
            return _bypass_to_validation(state)

        last_user = _last_user_msg(state)
        # Si la entrada de este nodo fue por "venir de free_capture", todavía
        # no hicimos las preguntas — las emitimos ahora.
        if state.awaiting_confirmation != "deep_dive_answers":
            return _emit_questions(state)

        # Vuelta siguiente: el usuario respondió. Lo persistimos como una
        # entrada única bajo la clave del tipo de documento.
        return _store_answers_and_advance(state, last_user or "")

    return deep_dive


# ===========================================================================
# Helpers
# ===========================================================================


def _last_user_msg(state: AgentState) -> str | None:
    for msg in reversed(state.messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            return content if isinstance(content, str) else None
    return None


def _emit_questions(state: AgentState) -> dict[str, Any]:
    assert state.classification is not None
    doc_type = str(state.classification.document_type)
    questions = QUESTIONS_BY_TYPE.get(doc_type, [])
    text = render("deep_dive_questions.j2", document_type=doc_type, questions=questions)
    message = _agent_message(state, content=text, stage="ETAPA_3")
    return {
        "messages": [message],
        "current_stage": "ETAPA_3",
        "previous_stage": state.current_stage,
        "needs_user_input": True,
        "awaiting_confirmation": "deep_dive_answers",
    }


def _store_answers_and_advance(state: AgentState, answer: str) -> Command:
    """Guarda la respuesta del usuario y delega a validation_summary
    en la misma vuelta para mostrar el resumen sin pausa intermedia."""
    assert state.classification is not None
    cleaned = answer.strip()
    new_qa = dict(state.deep_dive_qa)
    if cleaned:
        new_qa[f"Respuestas dirigidas {state.classification.document_type}"] = cleaned

    ack = "Perfecto, con esto ya tengo todo. Te muestro el resumen."
    message = _agent_message(state, content=ack, stage="ETAPA_3")
    return Command(
        goto="validation_summary",
        update={
            "messages": [message],
            "deep_dive_qa": new_qa,
            "current_stage": "ETAPA_3",
            "previous_stage": state.current_stage,
            "needs_user_input": False,
            "awaiting_confirmation": None,
        },
    )


def _bypass_to_validation(state: AgentState) -> dict[str, Any]:
    """Si llegamos sin clasificación (no debería pasar), saltamos a
    validation_summary para no quedar trabados."""
    return {
        "current_stage": "ETAPA_3",
        "previous_stage": state.current_stage,
        "needs_user_input": False,
        "awaiting_confirmation": None,
    }


def _agent_message(state: AgentState, *, content: str, stage: str) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": f"msg-dd-{state.session_id}-{len(state.messages)}",
        "role": "agent",
        "content": content,
        "stage": stage,
        "status": "complete",
        "started_at": now,
        "ended_at": now,
    }

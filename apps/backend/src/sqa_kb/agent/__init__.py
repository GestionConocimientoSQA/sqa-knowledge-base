"""Agente conversacional (Fase 2 — LangGraph).

Estructura del paquete:
- `state.py` — `AgentState` Pydantic (espejo §16.2 ROADMAP).
- `graph.py` — grafo principal y router (Fase 2.3+).
- `nodes/` — un módulo por ETAPA (Fase 2.3-2.5).
- `templates/` — Jinja2 con prompts del agente (Fase 2.2).
- `skills.py` — loader que inyecta skills al system prompt (Fase 2.2).
- `cost.py` — tracker de tokens/costo por sesión (Fase 2.2).
"""

from sqa_kb.agent.state import AgentState

__all__ = ["AgentState"]

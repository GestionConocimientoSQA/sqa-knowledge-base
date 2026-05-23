"""Nodos del grafo del agente.

Cada nodo es un *factory* (`make_<nombre>_node(gateway, repo, ...)`) que
devuelve una callable async compatible con LangGraph:

    async def node(state: AgentState) -> dict[str, Any]: ...

El factory permite inyectar dependencias (LLM gateway, repos) sin
acoplarlas a un singleton global — los tests pasan fakes y el grafo
arma se arma en `graph.py` con las instancias reales.

Nodos en 2.3:
- `welcome` — ETAPA 0: emite saludo + setea routing por modo.
- `identification` — ETAPA 1: extrae topic, busca KB, clasifica.

Nodos pendientes (2.4-2.5):
- free_capture, deep_dive, validation_summary, generate_document,
  score_capture, index_document (modo A).
- consult_search, synthesize_answer (modo B).
- ingestion_extract, classify_ingest, capture_traceability,
  index_ingestion (modo C).
"""

from sqa_kb.agent.nodes.identification import make_identification_node
from sqa_kb.agent.nodes.welcome import make_welcome_node

__all__ = ["make_identification_node", "make_welcome_node"]

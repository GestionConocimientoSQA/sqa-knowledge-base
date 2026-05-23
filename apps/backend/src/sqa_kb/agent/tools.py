"""Tools del agente — Fase 2.3.

Estos son los "tool calls" que los nodos del grafo invocan para tareas
discretas (buscar en KB, clasificar topic, scorear captura, anonimizar).

Diseño:
- **Funciones libres** que reciben sus dependencias por parámetro (gateway,
  repos). NO se inyectan via context global — facilita test sin patch.
- **Devuelven dataclasses o sub-modelos de `agent.state`** — el caller
  fusiona el resultado en el state via partial update.
- **Anthropic-agnostic**: dependen de `LlmGateway` (puerto), no del SDK.

Tools incluidas en 2.3:
- `search_kb(repo, query, top_k)`: full-text search sobre `documents.titulo`
  (stub — Fase 3 RAG agrega vector search + boost autoritativos).
- `classify_topic(gateway, topic, history)`: pide al LLM una sugerencia de
  carpeta + tipo + razón. Parsea JSON estructurado del response.

Tools que vienen en 2.4+:
- `score_capture` (ETAPA 5)
- `anonymize` (anonimizador, también ETAPA 5)
- `extract_text` (modo C ingestión, Fase 4 lo conecta a extractores)
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence

from sqa_kb.agent.state import CaptureScoring, Classification, ExistingDocument
from sqa_kb.ports.gateways import ChatMessage, LlmGateway
from sqa_kb.ports.repositories import DocumentRepository

logger = logging.getLogger(__name__)


# ===========================================================================
# search_kb (stub)
# ===========================================================================


async def search_kb(
    repo: DocumentRepository,
    *,
    query: str,
    top_k: int = 3,
) -> list[ExistingDocument]:
    """Busca documentos similares al `query` en el KB.

    **STUB**: usa `repo.search()` con el query textual (PostgreSQL ILIKE
    sobre `titulo + tags + autor_name`, Fase 1B.5). Devuelve dummy distance
    proporcional a la posición (0.30, 0.40, 0.50, ...). Fase 3 reemplaza
    por vector search real con embeddings + boost de autoritativos.

    El shape del resultado (`ExistingDocument`) ya es el correcto — solo
    cambia la implementación interna en Fase 3, los callers no se enteran.
    """
    if not query.strip():
        return []
    items, _total = await repo.search(query=query, limit=top_k, offset=0)
    result: list[ExistingDocument] = []
    for idx, doc in enumerate(items):
        result.append(
            ExistingDocument(
                document_id=doc.id,
                filename=doc.id + ".md",
                category=str(doc.carpeta),
                document_type=str(doc.tipo),
                # Distance creciente lineal con la posición (stub).
                # Fase 3: distance real del vector index.
                distance=round(0.30 + idx * 0.10, 2),
                created_at=doc.fecha.isoformat(),
            )
        )
    return result


# ===========================================================================
# classify_topic
# ===========================================================================


_CLASSIFY_SYSTEM_PROMPT = """\
Sos un clasificador del KB de SQA. Devolvés JSON con exactamente este shape:

{
  "category": "<PROC|TEC|ARQ|HERR|NEG|ENV|EST|CONT>",
  "document_type": "<POL|PROC|GUIA|INST|SERV|MTEC|ACEL|UEN|ARCL|FORM|PRES>",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<una línea explicando la decisión>"
}

Reglas:
- NO escribas texto fuera del JSON.
- NO uses markdown.
- Si no estás seguro, ponete confidence bajo y elegí la mejor opción razonable.
"""


async def classify_topic(
    gateway: LlmGateway,
    *,
    topic: str,
    history: Sequence[ChatMessage] = (),
    model: str | None = None,
) -> Classification:
    """Pide al LLM una clasificación estructurada para el `topic`.

    Args:
        gateway: implementación de `LlmGateway` (Anthropic real o fake).
        topic: tema detectado por el nodo de identificación.
        history: contexto previo (mensajes user/assistant) — el clasificador
                 los lee para entender mejor el dominio del topic.
        model: override del modelo (default el de settings).

    Lanza `ValueError` si el LLM devolvió algo que no es JSON parseable.
    El caller decide si reintentar o degradarse (p.ej. fallback a
    'CONT'/'GUIA' con confidence=0.0).
    """
    if not topic.strip():
        raise ValueError("topic vacío — el clasificador necesita un input")

    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=_CLASSIFY_SYSTEM_PROMPT),
        *history,
        ChatMessage(role="user", content=f"Topic a clasificar: {topic}"),
    ]
    completion = await gateway.complete(
        messages,
        model=model,
        max_tokens=512,
        temperature=0.0,  # determinístico — clasificación no debe variar
    )
    return _parse_classification(completion.text)


# ===========================================================================
# score_capture
# ===========================================================================


_SCORE_SYSTEM_PROMPT = """\
Sos un evaluador del valor del conocimiento capturado en el KB de SQA.
Devolvés JSON con exactamente este shape:

{
  "specificity": <int 1-5>,
  "depth": <int 1-5>,
  "reusability": <int 1-5>,
  "uniqueness": <int 1-5>,
  "value_score": <float 1.0-5.0>,
  "observations": "<una línea con razonamiento concreto>"
}

Criterios (escala 1=mínimo, 5=máximo):
- specificity: cuán concreto y accionable es (genérico vs. específico).
- depth: nivel de detalle técnico aportado.
- reusability: aplicabilidad en otros proyectos / clientes.
- uniqueness: aporta info nueva vs. ya existente en KB.
- value_score: promedio ponderado redondeado a 0.1.

NO escribas texto fuera del JSON. NO uses markdown.
"""


async def score_capture(
    gateway: LlmGateway,
    *,
    document_content: str,
    document_type: str,
    model: str | None = None,
) -> CaptureScoring:
    """Pide al LLM scoring de 4 dimensiones para el documento generado.

    Lanza `ValueError` si el JSON está malformado. Pydantic valida los
    ranges (1-5) en `CaptureScoring`.
    """
    if not document_content.strip():
        raise ValueError("document_content vacío — no se puede scorear")

    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=_SCORE_SYSTEM_PROMPT),
        ChatMessage(
            role="user",
            content=(
                f"Tipo de documento: {document_type}\n"
                f"Contenido:\n\n{document_content}"
            ),
        ),
    ]
    completion = await gateway.complete(
        messages,
        model=model,
        max_tokens=512,
        temperature=0.0,
    )
    return _parse_scoring(completion.text)


def _parse_scoring(raw: str) -> CaptureScoring:
    """Parsea el JSON del scoring. Misma robustez que `_parse_classification`."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"scorer devolvió no-JSON: {raw[:200]!r}") from exc

    # Coerce ints if model returned strings.
    for k in ("specificity", "depth", "reusability", "uniqueness"):
        if isinstance(data.get(k), str):
            try:
                data[k] = int(float(data[k]))
            except ValueError:
                data[k] = 1
    if isinstance(data.get("value_score"), str):
        try:
            data["value_score"] = float(data["value_score"])
        except ValueError:
            data["value_score"] = 1.0

    return CaptureScoring.model_validate(data)


def _parse_classification(raw: str) -> Classification:
    """Parsea el JSON crudo del LLM. Robusto a:
    - whitespace antes/después
    - bloque markdown ```json ... ``` aunque el prompt lo prohíba
    - confidence como string '0.8' o número 0.8
    """
    cleaned = raw.strip()
    # Algunos LLMs envuelven en markdown a pesar de las instrucciones.
    if cleaned.startswith("```"):
        # Saca primera línea (```json o ```) y última (```).
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"clasificador devolvió no-JSON: {raw[:200]!r}"
        ) from exc

    # confidence puede venir como string si el modelo decide narrar
    if isinstance(data.get("confidence"), str):
        try:
            data["confidence"] = float(data["confidence"])
        except ValueError:
            data["confidence"] = 0.0

    return Classification.model_validate(data)

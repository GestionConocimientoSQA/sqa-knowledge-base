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

from sqa_kb.agent.state import (
    CaptureScoring,
    Citation,
    Classification,
    ExistingDocument,
)
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


# ===========================================================================
# synthesize_consultation_answer (Fase 2.5 — modo B)
# ===========================================================================


_SYNTHESIS_SYSTEM_PROMPT = """\
Sos un asistente del KB de SQA respondiendo consultas. Te paso una
pregunta del usuario y los fragmentos (chunks) más relevantes del KB.

Reglas:
- Respondé en español neutro, técnico, directo. SIN preámbulos como
  "claro" o "por supuesto".
- Citá los documentos usando `[doc:document_id]` en el texto donde
  corresponda — el frontend resuelve la cita.
- Si los fragmentos no responden la pregunta, decilo explícito: "No
  encontré información directa sobre X en el KB" + sugerí captura.
- NO inventes datos, nombres de personas, fechas. Si la respuesta requiere
  algo que no está en los chunks, decilo.
- Una respuesta concisa vale más que una larga.
"""


async def synthesize_consultation_answer(
    gateway: LlmGateway,
    *,
    query: str,
    chunks: Sequence[dict[str, str]],
    model: str | None = None,
) -> str:
    """Pide al LLM una respuesta sintetizada para una consulta + chunks del KB.

    `chunks`: lista de dicts con keys `document_id`, `content`, `section_title`
    (opcional). Es lo que el retriever (Fase 3) devuelve normalizado.

    Devuelve el texto plano del LLM — el caller arma las citaciones
    aparte (basándose en los chunks consumidos).

    Lanza `ValueError` si la pregunta está vacía.
    """
    if not query.strip():
        raise ValueError("query vacía — el sintetizador necesita una pregunta")

    chunks_block = _format_chunks(chunks)
    user_prompt = (
        f"Pregunta del usuario:\n{query}\n\n"
        f"Fragmentos del KB:\n{chunks_block}"
    )
    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=_SYNTHESIS_SYSTEM_PROMPT),
        ChatMessage(role="user", content=user_prompt),
    ]
    completion = await gateway.complete(
        messages,
        model=model,
        max_tokens=1024,
        temperature=0.3,  # algo creativo pero anclado a los chunks
    )
    return completion.text.strip()


def _format_chunks(chunks: Sequence[dict[str, str]]) -> str:
    """Convierte los chunks en un bloque markdown para el prompt del LLM."""
    if not chunks:
        return "(sin resultados — el KB no tiene info directa)"
    parts: list[str] = []
    for idx, c in enumerate(chunks, start=1):
        section = c.get("section_title") or ""
        section_suffix = f" — *{section}*" if section else ""
        doc_id = c.get("document_id", "?")
        content = c.get("content", "")
        parts.append(f"[{idx}] [doc:{doc_id}]{section_suffix}\n{content}")
    return "\n\n".join(parts)


def build_citations_from_results(
    chunks: Sequence[dict[str, str]],
) -> list[Citation]:
    """Convierte chunks en `Citation` para guardar en state.

    Asigna `position` por orden recibido (1-indexed, espejo de cómo el
    LLM los referencia con [1], [2], ...).
    """
    out: list[Citation] = []
    for idx, c in enumerate(chunks, start=1):
        out.append(
            Citation(
                document_id=c.get("document_id", "?"),
                filename=c.get("filename", c.get("document_id", "?") + ".md"),
                chunk_id=c.get("chunk_id", f"chunk-{idx}"),
                section=c.get("section_title") or None,
                snippet=(c.get("content", "")[:200]),
                position=idx,
            )
        )
    return out


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

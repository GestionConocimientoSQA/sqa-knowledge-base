"""Tools del agente — Fase 2.3 (refactorizada en Fase 3.5).

Estos son los "tool calls" que los nodos del grafo invocan para tareas
discretas (buscar en KB, clasificar topic, scorear captura, anonimizar).

Diseño:
- **Funciones libres** que reciben sus dependencias por parámetro (gateway,
  searcher, repos). NO se inyectan via context global — facilita test sin patch.
- **Devuelven dataclasses o sub-modelos de `agent.state`** — el caller
  fusiona el resultado en el state via partial update.
- **Anthropic-agnostic**: dependen de `LlmGateway` (puerto), no del SDK.

Tools incluidas:
- `search_kb(searcher, query, top_k)`: hybrid search vector + FTS,
  agrupa chunks por documento y devuelve `ExistingDocument[]` con
  `distance = 1 - score`. Reemplaza el stub full-text de Fase 2.3.
- `search_kb_chunks(searcher, query, top_k)`: variante que devuelve
  los chunks crudos con `content`/`snippet` (úsala para sintetizar
  respuestas en modo B).
- `classify_topic(gateway, topic, history)`: pide al LLM una sugerencia
  de carpeta + tipo + razón.
- `synthesize_consultation_answer(gateway, query, chunks)`: arma la
  respuesta del modo B con citas inline.
- `build_citations_from_results(chunks)`: convierte chunks a citaciones
  para state.

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
from sqa_kb.rag.hybrid_search import HybridChunk, HybridSearcher

logger = logging.getLogger(__name__)


# ===========================================================================
# search_kb (RAG real — Fase 3.5)
# ===========================================================================
#
# `search_kb` agrupa los chunks devueltos por el `HybridSearcher` en
# `ExistingDocument` (un row por document_id). El score combinado del
# hybrid searcher está en [0, ~boost]; lo convertimos a `distance =
# clip(1 - score, 0, 1)` para mantener la semántica del state del agente
# (ETAPA 1 compara contra `DUPLICATE_THRESHOLD = 0.55` desde antes de
# Fase 3 — el contrato no cambia, solo la implementación).
#
# Para conseguir K docs únicos, el caller no sabe cuántos chunks van a
# colapsar. Pedimos `top_k * CHUNK_OVERSAMPLE` chunks al searcher y
# dedupeamos por `document_id` quedándonos con el de mejor score.
# Oversample = 5 cubre el caso común; si en la práctica documentos muy
# largos colapsan más chunks, el caller puede pedir más top_k.

CHUNK_OVERSAMPLE: int = 5
"""Multiplicador para pedir más chunks al searcher antes de dedupear
por `document_id`. Calibrado para que `top_k=3` pida 15 chunks y casi
siempre alcance para 3 docs únicos."""


async def search_kb(
    searcher: HybridSearcher,
    *,
    query: str,
    top_k: int = 3,
) -> list[ExistingDocument]:
    """Busca documentos similares al `query` en el KB usando hybrid search.

    Devuelve hasta `top_k` documentos únicos ordenados por relevancia
    (mejor score primero). `distance = 1 - score` — los nodos del agente
    (identification, consultation) comparan contra `DUPLICATE_THRESHOLD`
    y `HIGH/MEDIUM_RELEVANCE_THRESHOLD` con esa semántica.
    """
    if not query.strip():
        return []
    chunks = await searcher.search(query, top_k=top_k * CHUNK_OVERSAMPLE)
    if not chunks:
        return []

    # Dedupe por document_id quedándonos con el chunk de mejor score.
    # Los chunks ya vienen ordenados desc por score (ROADMAP §17.5), así
    # que el primer chunk visto de cada doc es el ganador.
    best_by_doc: dict[str, HybridChunk] = {}
    for chunk in chunks:
        if chunk.document_id not in best_by_doc:
            best_by_doc[chunk.document_id] = chunk
        if len(best_by_doc) >= top_k:
            break

    result: list[ExistingDocument] = []
    for chunk in best_by_doc.values():
        # `distance = clip(1 - score, 0, 1)`. El boost autoritativo puede
        # llevar score > 1; truncamos para que distance no quede negativa
        # y rompa los thresholds.
        distance = max(0.0, min(1.0, 1.0 - chunk.score))
        result.append(
            ExistingDocument(
                document_id=chunk.document_id,
                # `filename` es un alias derivado — Fase 4 lo reemplazará
                # con el nombre real del blob cuando exista upload.
                filename=chunk.document_id + ".md",
                category=chunk.document_category,
                document_type=chunk.document_type,
                distance=round(distance, 4),
                # Sin acceso a la fecha del doc desde el chunk — el
                # `HybridChunk` no la trae para mantener payload chico.
                # Pasamos string vacío (el frontend lo trata como "—").
                # Si el nodo necesita la fecha, hace un repo.get(doc_id).
                created_at="",
            )
        )
    return result


async def search_kb_chunks(
    searcher: HybridSearcher,
    *,
    query: str,
    top_k: int = 5,
) -> Sequence[HybridChunk]:
    """Variante que devuelve los chunks crudos del hybrid search.

    Útil para nodos que necesitan el `content` del chunk (consultation
    para sintetizar respuesta, generation para citar) — no solo el
    document_id como `search_kb`. Sin dedupe ni agregación: el caller
    decide qué hacer con múltiples chunks del mismo doc.
    """
    if not query.strip():
        return []
    return await searcher.search(query, top_k=top_k)


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

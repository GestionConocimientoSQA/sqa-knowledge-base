"""Eval set + métricas del RAG (Fase 3.7).

Este módulo NO mide calidad semántica de Cohere — eso queda para
validación dual con TI (Fase 11). Mide que el **pipeline completo**
del RAG funciona end-to-end: chunker → embedder port → SQL hybrid →
ranking final. El usuario corre el eval con un `FakeEmbedder` que
devuelve vectores deterministas y verifica que los docs esperados
salgan en el top-K.

**Métricas implementadas (ROADMAP §17.8)**:
- `recall@5`: cuántos de los docs "relevantes" para una query aparecen
  en el top-5 retornado / cuántos relevantes hay en total.
- `precision@1`: el doc top-1 retornado pertenece al set de relevantes
  (1.0) o no (0.0).

**Umbrales del DoD de Fase 3 completa**:
- `recall@5_avg ≥ 0.90`
- `precision@1_avg ≥ 0.75`

**Re-correr con Cohere real** cuando se habilite: cambiar el adapter
inyectado al `HybridSearcher` de `FakeEmbedder` a `CohereEmbedder`.
El resto del flujo es idéntico.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from sqa_kb.rag.hybrid_search import HybridChunk

# Umbrales DoD Fase 3 (ROADMAP §17.8). Configurables por CLI pero acá
# están como defaults canónicos.
DEFAULT_RECALL_THRESHOLD: float = 0.90
DEFAULT_PRECISION_THRESHOLD: float = 0.75
DEFAULT_TOP_K: int = 5


@dataclass(frozen=True, slots=True)
class EvalCase:
    """Un item del eval set.

    `query_vector_seed` permite que el script CLI use un `FakeEmbedder`
    determinista. Cuando se mida con Cohere real este campo se ignora
    (el adapter consume `query_text` directamente).
    """

    query_id: str
    query_text: str
    query_vector_seed: float
    expected_top_doc_id: str
    expected_relevant_doc_ids: tuple[str, ...]
    """Para `recall@5`. El `expected_top_doc_id` debería estar incluido."""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class CaseResult:
    """Resultado por caso individual."""

    query_id: str
    retrieved_doc_ids: tuple[str, ...]
    """En orden — `[0]` es el top-1."""
    recall_at_k: float
    precision_at_1: float
    expected_top_doc_id: str
    actual_top_doc_id: str | None


@dataclass(frozen=True, slots=True)
class EvalResult:
    """Resultado agregado de una corrida completa del eval."""

    cases: tuple[CaseResult, ...]
    recall_at_k_avg: float
    precision_at_1_avg: float
    k: int
    cases_passed_recall: int
    """Cuántos casos individuales alcanzaron recall@k = 1.0."""
    cases_passed_precision: int

    @property
    def total_cases(self) -> int:
        return len(self.cases)


# ===========================================================================
# Métricas puras (sin side effects, fáciles de testear)
# ===========================================================================


def compute_recall_at_k(
    expected: Sequence[str],
    retrieved: Sequence[str],
    *,
    k: int = DEFAULT_TOP_K,
) -> float:
    """Fracción de `expected` que aparece en los primeros `k` de `retrieved`.

    Edge cases:
    - `expected` vacío → 1.0 (no había nada que recuperar — trivialmente OK).
    - `k <= 0` → 0.0.
    - `retrieved` vacío → 0.0 si había algo esperado.
    """
    if not expected:
        return 1.0
    if k <= 0 or not retrieved:
        return 0.0
    top_k = set(retrieved[:k])
    hits = sum(1 for doc_id in expected if doc_id in top_k)
    return hits / len(expected)


def compute_precision_at_1(
    expected_relevant: Sequence[str],
    retrieved: Sequence[str],
) -> float:
    """1.0 si el top-1 retornado está en el set de relevantes, si no 0.0.

    Edge cases:
    - `retrieved` vacío → 0.0.
    - `expected_relevant` vacío → 0.0 (no se puede acertar el top-1 si
      no hay ninguno relevante).
    """
    if not retrieved or not expected_relevant:
        return 0.0
    return 1.0 if retrieved[0] in set(expected_relevant) else 0.0


# ===========================================================================
# Carga del eval set desde JSONL
# ===========================================================================


def load_eval_set(path: Path) -> list[EvalCase]:
    """Lee un archivo JSONL (un caso por línea) y devuelve `EvalCase`s.

    Lanza `ValueError` si una línea no tiene los campos requeridos, con
    mensaje claro indicando el número de línea.
    """
    cases: list[EvalCase] = []
    with path.open("r", encoding="utf-8") as fp:
        for line_no, raw in enumerate(fp, start=1):
            line = raw.strip()
            if not line or line.startswith("//"):
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"línea {line_no}: JSON inválido — {exc}"
                ) from exc
            try:
                cases.append(_case_from_dict(data))
            except KeyError as exc:
                raise ValueError(
                    f"línea {line_no}: falta campo {exc}"
                ) from exc
    return cases


def _case_from_dict(data: dict) -> EvalCase:  # type: ignore[type-arg]
    """Convierte un dict (desde JSONL) a `EvalCase`. Valida campos
    obligatorios; los opcionales caen a su default."""
    return EvalCase(
        query_id=data["query_id"],
        query_text=data["query_text"],
        query_vector_seed=float(data["query_vector_seed"]),
        expected_top_doc_id=data["expected_top_doc_id"],
        expected_relevant_doc_ids=tuple(data["expected_relevant_doc_ids"]),
        notes=str(data.get("notes", "")),
    )


# ===========================================================================
# Tipo del callable que ejecuta la búsqueda
# ===========================================================================


SearchFn = Callable[[EvalCase], Awaitable[Sequence[HybridChunk]]]
"""Función inyectable que recibe un `EvalCase` y devuelve los chunks
top-K. El CLI la cablea a `HybridSearcher.search(case.query_text)`
con un embedder fake que mapea `query_text -> vector(seed)`. Los tests
pueden inyectar cualquier callable que devuelva chunks fake."""


# ===========================================================================
# Run end-to-end
# ===========================================================================


async def run_eval(
    cases: Sequence[EvalCase],
    *,
    search_fn: SearchFn,
    k: int = DEFAULT_TOP_K,
) -> EvalResult:
    """Ejecuta el eval completo y devuelve métricas agregadas.

    Args:
        cases: lista de EvalCase a evaluar.
        search_fn: función async que ejecuta la búsqueda. El caller
            la construye con `HybridSearcher` real + `FakeEmbedder`
            (en CLI) o con un searcher fake (en tests).
        k: top-K para `recall@k`.

    Para cada caso:
    1. Llama `search_fn(case)` → chunks top-K.
    2. Extrae `document_id` de cada chunk preservando orden.
    3. Computa `recall@k` y `precision@1`.
    4. Acumula.

    Al final calcula promedios y conteo de casos que pasaron umbral 1.0
    individual.
    """
    case_results: list[CaseResult] = []
    recall_sum = 0.0
    precision_sum = 0.0
    passed_recall = 0
    passed_precision = 0

    for case in cases:
        chunks = await search_fn(case)
        # Preservamos orden y dedupeamos por document_id (varios chunks
        # del mismo doc cuentan como un solo hit para precision@1).
        retrieved_ids: list[str] = []
        seen: set[str] = set()
        for chunk in chunks:
            if chunk.document_id not in seen:
                retrieved_ids.append(chunk.document_id)
                seen.add(chunk.document_id)

        recall = compute_recall_at_k(
            case.expected_relevant_doc_ids, retrieved_ids, k=k
        )
        precision = compute_precision_at_1(
            case.expected_relevant_doc_ids, retrieved_ids
        )
        recall_sum += recall
        precision_sum += precision
        if recall >= 1.0:
            passed_recall += 1
        if precision >= 1.0:
            passed_precision += 1

        case_results.append(
            CaseResult(
                query_id=case.query_id,
                retrieved_doc_ids=tuple(retrieved_ids),
                recall_at_k=recall,
                precision_at_1=precision,
                expected_top_doc_id=case.expected_top_doc_id,
                actual_top_doc_id=retrieved_ids[0] if retrieved_ids else None,
            )
        )

    total = len(case_results) if case_results else 1
    return EvalResult(
        cases=tuple(case_results),
        recall_at_k_avg=recall_sum / total,
        precision_at_1_avg=precision_sum / total,
        k=k,
        cases_passed_recall=passed_recall,
        cases_passed_precision=passed_precision,
    )


def meets_thresholds(
    result: EvalResult,
    *,
    recall_threshold: float = DEFAULT_RECALL_THRESHOLD,
    precision_threshold: float = DEFAULT_PRECISION_THRESHOLD,
) -> bool:
    """True si AMBAS métricas promedio alcanzaron sus umbrales DoD."""
    return (
        result.recall_at_k_avg >= recall_threshold
        and result.precision_at_1_avg >= precision_threshold
    )

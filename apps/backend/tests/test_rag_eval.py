"""Tests del módulo `rag/eval` (Fase 3.7).

Cubren las funciones puras (recall@k, precision@1), parsing del JSONL,
y la corrida `run_eval` con un `search_fn` fake.

Sin DB ni Cohere — todos los fakes son in-memory.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from sqa_kb.rag.eval import (
    DEFAULT_PRECISION_THRESHOLD,
    DEFAULT_RECALL_THRESHOLD,
    DEFAULT_TOP_K,
    CaseResult,
    EvalCase,
    EvalResult,
    compute_precision_at_1,
    compute_recall_at_k,
    load_eval_set,
    meets_thresholds,
    run_eval,
)
from sqa_kb.rag.hybrid_search import HybridChunk


# ===========================================================================
# compute_recall_at_k
# ===========================================================================


def test_recall_at_k_all_expected_in_top_k() -> None:
    expected = ["A", "B"]
    retrieved = ["A", "C", "B", "D", "E"]
    assert compute_recall_at_k(expected, retrieved, k=5) == pytest.approx(1.0)


def test_recall_at_k_partial_match() -> None:
    expected = ["A", "B", "C"]
    retrieved = ["A", "X", "Y", "Z", "B"]  # falta C
    assert compute_recall_at_k(expected, retrieved, k=5) == pytest.approx(2 / 3)


def test_recall_at_k_no_match() -> None:
    expected = ["A", "B"]
    retrieved = ["X", "Y", "Z"]
    assert compute_recall_at_k(expected, retrieved, k=5) == 0.0


def test_recall_at_k_empty_expected_is_one() -> None:
    """Caso edge: no había nada esperado → trivialmente OK."""
    assert compute_recall_at_k([], ["X"], k=5) == 1.0


def test_recall_at_k_empty_retrieved_zero() -> None:
    assert compute_recall_at_k(["A"], [], k=5) == 0.0


def test_recall_at_k_k_truncates_window() -> None:
    """`A` está en top-3 pero no en top-2 → recall@2 = 0."""
    expected = ["A"]
    retrieved = ["X", "Y", "A"]
    assert compute_recall_at_k(expected, retrieved, k=2) == 0.0
    assert compute_recall_at_k(expected, retrieved, k=3) == 1.0


def test_recall_at_k_zero_or_negative_k_returns_zero() -> None:
    expected = ["A"]
    retrieved = ["A"]
    assert compute_recall_at_k(expected, retrieved, k=0) == 0.0
    assert compute_recall_at_k(expected, retrieved, k=-1) == 0.0


# ===========================================================================
# compute_precision_at_1
# ===========================================================================


def test_precision_at_1_top_in_expected() -> None:
    assert compute_precision_at_1(["A", "B"], ["A", "X", "Y"]) == 1.0


def test_precision_at_1_top_not_in_expected() -> None:
    assert compute_precision_at_1(["A", "B"], ["X", "A", "B"]) == 0.0


def test_precision_at_1_empty_retrieved_zero() -> None:
    assert compute_precision_at_1(["A"], []) == 0.0


def test_precision_at_1_empty_expected_zero() -> None:
    assert compute_precision_at_1([], ["A"]) == 0.0


# ===========================================================================
# load_eval_set
# ===========================================================================


def test_load_eval_set_reads_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "set.jsonl"
    path.write_text(
        json.dumps(
            {
                "query_id": "Q01",
                "query_text": "playwright e2e",
                "query_vector_seed": 0.7,
                "expected_top_doc_id": "TEC-pw",
                "expected_relevant_doc_ids": ["TEC-pw", "TEC-cypress"],
                "notes": "match léxico",
            }
        )
        + "\n"
        + json.dumps(
            {
                "query_id": "Q02",
                "query_text": "selenium grid",
                "query_vector_seed": 0.3,
                "expected_top_doc_id": "TEC-sel",
                "expected_relevant_doc_ids": ["TEC-sel"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    cases = load_eval_set(path)
    assert len(cases) == 2
    assert cases[0].query_id == "Q01"
    assert cases[0].query_vector_seed == pytest.approx(0.7)
    assert cases[0].expected_relevant_doc_ids == ("TEC-pw", "TEC-cypress")
    assert cases[0].notes == "match léxico"
    assert cases[1].notes == ""  # default


def test_load_eval_set_skips_empty_and_comment_lines(tmp_path: Path) -> None:
    path = tmp_path / "set.jsonl"
    path.write_text(
        "// comentario\n"
        "\n"
        + json.dumps(
            {
                "query_id": "Q01",
                "query_text": "x",
                "query_vector_seed": 0.1,
                "expected_top_doc_id": "A",
                "expected_relevant_doc_ids": ["A"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    cases = load_eval_set(path)
    assert len(cases) == 1


def test_load_eval_set_invalid_json_raises_with_line_number(
    tmp_path: Path,
) -> None:
    path = tmp_path / "set.jsonl"
    path.write_text(
        json.dumps(
            {
                "query_id": "Q01",
                "query_text": "x",
                "query_vector_seed": 0.1,
                "expected_top_doc_id": "A",
                "expected_relevant_doc_ids": ["A"],
            }
        )
        + "\n{ broken json\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="línea 2"):
        load_eval_set(path)


def test_load_eval_set_missing_field_raises_with_line_number(
    tmp_path: Path,
) -> None:
    """Falta `expected_top_doc_id` en la segunda línea."""
    path = tmp_path / "set.jsonl"
    path.write_text(
        json.dumps(
            {
                "query_id": "Q01",
                "query_text": "x",
                "query_vector_seed": 0.1,
                "expected_top_doc_id": "A",
                "expected_relevant_doc_ids": ["A"],
            }
        )
        + "\n"
        + json.dumps({"query_id": "Q02", "query_text": "y", "query_vector_seed": 0.2})
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="línea 2"):
        load_eval_set(path)


# ===========================================================================
# run_eval con search_fn fake
# ===========================================================================


def _chunk(*, doc_id: str, chunk_id: str | None = None, score: float = 0.8) -> HybridChunk:
    return HybridChunk(
        chunk_id=chunk_id or f"chk-{doc_id}",
        document_id=doc_id,
        chunk_index=0,
        content="contenido",
        snippet="contenido",
        section_title="",
        score=score,
        vector_score=score,
        fulltext_score=0.0,
        document_title=doc_id,
        document_type="POL",
        document_category="TEC",
        authoritative=False,
    )


async def test_run_eval_aggregates_metrics() -> None:
    cases = [
        EvalCase(
            query_id="Q01",
            query_text="x",
            query_vector_seed=0.7,
            expected_top_doc_id="A",
            expected_relevant_doc_ids=("A", "B"),
        ),
        EvalCase(
            query_id="Q02",
            query_text="y",
            query_vector_seed=0.3,
            expected_top_doc_id="C",
            expected_relevant_doc_ids=("C",),
        ),
    ]
    # Search devuelve hits perfectos para ambos casos.
    routes: dict[str, list[HybridChunk]] = {
        "Q01": [_chunk(doc_id="A"), _chunk(doc_id="B")],
        "Q02": [_chunk(doc_id="C")],
    }

    async def _fake_search(case: EvalCase) -> Sequence[HybridChunk]:
        return routes[case.query_id]

    result = await run_eval(cases, search_fn=_fake_search, k=5)
    assert result.total_cases == 2
    assert result.recall_at_k_avg == pytest.approx(1.0)
    assert result.precision_at_1_avg == pytest.approx(1.0)
    assert result.cases_passed_recall == 2
    assert result.cases_passed_precision == 2


async def test_run_eval_mixed_results() -> None:
    """Caso 1 acierta perfecto, caso 2 falla recall y precision."""
    cases = [
        EvalCase(
            query_id="Q01",
            query_text="x",
            query_vector_seed=0.7,
            expected_top_doc_id="A",
            expected_relevant_doc_ids=("A", "B"),
        ),
        EvalCase(
            query_id="Q02",
            query_text="y",
            query_vector_seed=0.3,
            expected_top_doc_id="C",
            expected_relevant_doc_ids=("C", "D"),
        ),
    ]
    routes: dict[str, list[HybridChunk]] = {
        "Q01": [_chunk(doc_id="A"), _chunk(doc_id="B")],
        # Caso 2: top-1 incorrecto (X en lugar de C) y solo aparece D.
        "Q02": [_chunk(doc_id="X"), _chunk(doc_id="D")],
    }

    async def _fake_search(case: EvalCase) -> Sequence[HybridChunk]:
        return routes[case.query_id]

    result = await run_eval(cases, search_fn=_fake_search, k=5)
    # Q01: recall=1, precision=1. Q02: recall=0.5 (D de 2), precision=0.
    assert result.recall_at_k_avg == pytest.approx(0.75)
    assert result.precision_at_1_avg == pytest.approx(0.5)
    assert result.cases_passed_recall == 1
    assert result.cases_passed_precision == 1


async def test_run_eval_dedupes_chunks_by_doc_for_metrics() -> None:
    """Varios chunks del mismo doc cuentan como 1 hit (no inflar recall)."""
    cases = [
        EvalCase(
            query_id="Q01",
            query_text="x",
            query_vector_seed=0.5,
            expected_top_doc_id="A",
            expected_relevant_doc_ids=("A", "B"),
        ),
    ]
    routes = {
        # 3 chunks de A + nada de B → recall debe ser 0.5, no 1.5.
        "Q01": [
            _chunk(doc_id="A", chunk_id="c1"),
            _chunk(doc_id="A", chunk_id="c2"),
            _chunk(doc_id="A", chunk_id="c3"),
        ],
    }

    async def _fake_search(case: EvalCase) -> Sequence[HybridChunk]:
        return routes[case.query_id]

    result = await run_eval(cases, search_fn=_fake_search)
    assert result.cases[0].retrieved_doc_ids == ("A",)
    assert result.recall_at_k_avg == pytest.approx(0.5)
    # Top-1 es A, que SI está en expected.
    assert result.precision_at_1_avg == pytest.approx(1.0)


async def test_run_eval_empty_retrieval_metrics_zero() -> None:
    cases = [
        EvalCase(
            query_id="Q01",
            query_text="x",
            query_vector_seed=0.5,
            expected_top_doc_id="A",
            expected_relevant_doc_ids=("A",),
        ),
    ]

    async def _empty(case: EvalCase) -> Sequence[HybridChunk]:  # noqa: ARG001
        return []

    result = await run_eval(cases, search_fn=_empty)
    assert result.cases[0].actual_top_doc_id is None
    assert result.recall_at_k_avg == 0.0
    assert result.precision_at_1_avg == 0.0


async def test_run_eval_empty_cases_returns_zero_total_cases() -> None:
    async def _never_called(case: EvalCase) -> Sequence[HybridChunk]:  # noqa: ARG001
        raise AssertionError("no debería llamarse")

    result = await run_eval([], search_fn=_never_called)
    assert result.total_cases == 0
    # Las divisiones usan el denominador 1 cuando no hay casos para
    # evitar ZeroDivisionError; los promedios quedan en 0.
    assert result.recall_at_k_avg == 0.0
    assert result.precision_at_1_avg == 0.0


# ===========================================================================
# meets_thresholds
# ===========================================================================


def test_meets_thresholds_passes_both() -> None:
    result = EvalResult(
        cases=(),
        recall_at_k_avg=0.95,
        precision_at_1_avg=0.80,
        k=5,
        cases_passed_recall=10,
        cases_passed_precision=8,
    )
    assert meets_thresholds(result) is True


def test_meets_thresholds_fails_recall() -> None:
    result = EvalResult(
        cases=(),
        recall_at_k_avg=0.85,  # < 0.90
        precision_at_1_avg=0.80,
        k=5,
        cases_passed_recall=8,
        cases_passed_precision=8,
    )
    assert meets_thresholds(result) is False


def test_meets_thresholds_fails_precision() -> None:
    result = EvalResult(
        cases=(),
        recall_at_k_avg=0.95,
        precision_at_1_avg=0.70,  # < 0.75
        k=5,
        cases_passed_recall=10,
        cases_passed_precision=7,
    )
    assert meets_thresholds(result) is False


def test_meets_thresholds_custom_thresholds() -> None:
    result = EvalResult(
        cases=(),
        recall_at_k_avg=0.50,
        precision_at_1_avg=0.50,
        k=5,
        cases_passed_recall=5,
        cases_passed_precision=5,
    )
    assert meets_thresholds(result, recall_threshold=0.4, precision_threshold=0.4) is True


# ===========================================================================
# Constants sanity
# ===========================================================================


def test_default_constants() -> None:
    """Smoke: las constantes coinciden con ROADMAP §17.8."""
    assert DEFAULT_RECALL_THRESHOLD == 0.90
    assert DEFAULT_PRECISION_THRESHOLD == 0.75
    assert DEFAULT_TOP_K == 5


# Tipos exportados — sanity
def test_case_result_has_expected_fields() -> None:
    r = CaseResult(
        query_id="Q",
        retrieved_doc_ids=("A",),
        recall_at_k=1.0,
        precision_at_1=1.0,
        expected_top_doc_id="A",
        actual_top_doc_id="A",
    )
    assert r.query_id == "Q"

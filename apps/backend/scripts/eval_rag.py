"""CLI del eval del RAG (Fase 3.7).

Mide `recall@5` y `precision@1` del pipeline completo
(chunker → embedder → SQL hybrid → ranking) contra un corpus sintético
y un eval set curado en `tests/fixtures/eval_set.jsonl`.

**NO usa Cohere real** — la regla activa del proyecto. El `FakeEmbedder`
mapea cada `query_text` a un vector determinista basado en el
`query_vector_seed` del eval set. Los chunks sembrados con `--seed-data`
tienen vectores en slots únicos del espacio 1024-dim para que el ranking
sea predecible.

Para re-correr con Cohere real (validación dual con TI, Fase 11):
reemplazar el `FakeEmbedder` por `CohereEmbedder` con la key real.
El resto del pipeline es idéntico.

Uso típico:

    # Sembrar la DB con corpus + correr eval
    python scripts/eval_rag.py --seed-data

    # Solo correr eval (asume DB ya sembrada)
    python scripts/eval_rag.py

    # Eval set custom
    python scripts/eval_rag.py --eval-set otra/ruta.jsonl

Exit codes:
    0 — recall@5 ≥ umbral AND precision@1 ≥ umbral
    1 — métricas debajo de umbrales
    2 — config inválida (sin DATABASE_URL, etc.)
    3 — crash inesperado
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from sqlalchemy import text

from sqa_kb.adapters.repositories.postgres import (
    create_engine,
    create_session_factory,
)
from sqa_kb.adapters.repositories.postgres import models
from sqa_kb.adapters.repositories.postgres.chunks import PostgresChunkRepository
from sqa_kb.adapters.repositories.postgres.session import session_scope
from sqa_kb.config import Settings, get_settings
from sqa_kb.domain.entities import DocumentChunk
from sqa_kb.domain.errors import ExternalServiceError
from sqa_kb.ports.gateways import EmbeddingBatch
from sqa_kb.rag.eval import (
    DEFAULT_PRECISION_THRESHOLD,
    DEFAULT_RECALL_THRESHOLD,
    DEFAULT_TOP_K,
    EvalCase,
    EvalResult,
    load_eval_set,
    meets_thresholds,
    run_eval,
)
from sqa_kb.rag.hybrid_search import HybridChunk, HybridSearcher

logger = logging.getLogger(__name__)


# ===========================================================================
# Corpus sintético
# ===========================================================================
#
# Cada doc apunta a un "slot" único del vector 1024-dim. El chunk del
# doc tiene vector `unit_vector(slot)` (1 en la posición `slot`, 0 en
# todas las demás). Las queries del eval set tienen `query_vector_seed`
# que mapea al mismo slot del doc top-1 esperado → cosine match perfecto.
#
# Para queries `multi-relevant`, el FakeEmbedder genera un vector que
# es combinación de los slots de los docs relevantes (normalizado).

EVAL_DOC_PREFIX = "EVAL"
"""Prefijo del slug para que los docs del eval no contaminen búsquedas
del usuario real. El seed_data() los identifica por este prefijo."""


@dataclass(frozen=True, slots=True)
class _EvalDoc:
    doc_id: str
    titulo: str
    carpeta: str
    tipo: str
    content: str
    slot: int


# 30 docs sintéticos. Los IDs coinciden con los `expected_*` del eval_set.jsonl.
EVAL_CORPUS: tuple[_EvalDoc, ...] = (
    _EvalDoc("TEC-playwright-setup-2026-01-10", "Setup Playwright e2e", "TEC", "MTEC",
             "Guía para configurar Playwright como framework de tests end-to-end "
             "incluyendo fixtures, workers paralelos y reporters JSON.", 0),
    _EvalDoc("TEC-cypress-vs-playwright-2026-02-15", "Cypress vs Playwright", "TEC", "MTEC",
             "Comparativa entre Cypress y Playwright en velocidad, soporte multi-browser, "
             "auto-waiting y debugging. Conclusión: Playwright gana en cross-browser.", 1),
    _EvalDoc("TEC-selenium-grid-2026-03-01", "Selenium Grid distribuido", "TEC", "MTEC",
             "Cómo configurar un hub Selenium Grid con nodos distribuidos para correr "
             "suites en paralelo sobre múltiples navegadores.", 2),
    _EvalDoc("TEC-flaky-tests-2026-01-20", "Detección de flaky tests", "TEC", "GUIA",
             "Estrategias para detectar y mitigar tests flaky: retry pattern, "
             "test quarantine, análisis estadístico de runs.", 3),
    _EvalDoc("TEC-contract-testing-pact-2026-04-05", "Contract testing con Pact", "TEC", "GUIA",
             "Implementación de contract testing entre microservicios usando Pact "
             "broker, consumer-driven contracts y verificación CI.", 4),
    _EvalDoc("TEC-performance-k6-2026-04-12", "Performance testing con k6", "TEC", "GUIA",
             "Tests de carga con k6.io. Definición de escenarios, thresholds de SLA, "
             "integración con Grafana para dashboards.", 5),
    _EvalDoc("TEC-load-testing-jmeter-2026-05-01", "Load testing con JMeter", "TEC", "GUIA",
             "JMeter para tests de carga: thread groups, rampup, controllers, "
             "listeners, integración con Maven.", 6),
    _EvalDoc("TEC-api-postman-2026-02-20", "API testing con Postman", "TEC", "GUIA",
             "Postman Collections para API testing: environments, pre-request scripts, "
             "tests scripts, Newman CLI.", 7),
    _EvalDoc("TEC-mobile-appium-2026-03-10", "Mobile testing con Appium", "TEC", "GUIA",
             "Appium para iOS y Android: capabilities, locators, gestures, "
             "integración con devices farms.", 8),
    _EvalDoc("TEC-a11y-axe-2026-04-22", "Accessibility testing con axe", "TEC", "GUIA",
             "axe-core para verificación WCAG 2.1 AA. Integración con Playwright, "
             "Cypress y Selenium. Reglas + best practices.", 9),
    _EvalDoc("PROC-code-review-2026-01-15", "Procedimiento de revisión de código", "PROC", "PROC",
             "Procedimiento de code review: checklist, criterios de aprobación, "
             "tiempos máximos de respuesta, roles del reviewer.", 10),
    _EvalDoc("PROC-ingesta-kb-2026-02-08", "Proceso de ingesta al KB", "PROC", "PROC",
             "Cómo ingresar documentos aprobados al knowledge base: clasificación, "
             "trazabilidad, anonimización, indexación vectorial.", 11),
    _EvalDoc("POL-retencion-datos-2026-03-20", "Política de retención de datos", "PROC", "POL",
             "Política de retención de datos personales según GDPR: tiempos, "
             "anonimización, derecho al olvido, audit trail.", 12),
    _EvalDoc("POL-secrets-vault-2026-04-01", "Política de secrets en Key Vault", "PROC", "POL",
             "Política de gestión de secrets con Azure Key Vault: rotación, "
             "RBAC, access policies, audit logs.", 13),
    _EvalDoc("ARQ-microservicios-eventos-2026-02-25", "Microservicios y eventos", "ARQ", "MTEC",
             "Arquitectura de microservicios con event-driven communication, "
             "Kafka, dead letter queues, eventual consistency.", 14),
    _EvalDoc("ARQ-event-sourcing-2026-03-15", "Event sourcing y CQRS", "ARQ", "MTEC",
             "Patrón event sourcing combinado con CQRS para sistemas distribuidos. "
             "Snapshots, projections, replay.", 15),
    _EvalDoc("HERR-github-actions-2026-01-05", "Herramienta GitHub Actions", "HERR", "GUIA",
             "GitHub Actions para CI/CD: workflows, reusable workflows, secrets, "
             "OIDC federation con Azure.", 16),
    _EvalDoc("HERR-docker-compose-2026-02-12", "Herramienta Docker Compose", "HERR", "GUIA",
             "Docker Compose para desarrollo local: services, networks, volumes, "
             "healthchecks, override files.", 17),
    _EvalDoc("INST-onboarding-2026-03-25", "Onboarding de nuevo colaborador", "PROC", "INST",
             "Instructivo paso a paso para onboarding de nuevos colaboradores: "
             "accesos, setup de tooling, primer pull request.", 18),
    _EvalDoc("MTEC-migracion-postgres-2026-04-18", "Migración a PostgreSQL", "TEC", "MTEC",
             "Memoria técnica de la migración desde SQL Server a PostgreSQL Flexible "
             "Server: extensions, performance tuning, downtime.", 19),
    # Distractores — docs que NO esperamos que matcheen ningún query.
    # Slots 20-29.
    _EvalDoc("TEC-distractor-001-2026-01-01", "Distractor 1", "TEC", "GUIA",
             "Contenido genérico sobre un tema no buscado.", 20),
    _EvalDoc("TEC-distractor-002-2026-01-02", "Distractor 2", "TEC", "GUIA",
             "Otro contenido genérico distinto.", 21),
    _EvalDoc("PROC-distractor-003-2026-01-03", "Distractor 3", "PROC", "PROC",
             "Procedimiento administrativo sin relación.", 22),
    _EvalDoc("ARQ-distractor-004-2026-01-04", "Distractor 4", "ARQ", "MTEC",
             "Detalle arquitectónico de bajo nivel.", 23),
    _EvalDoc("HERR-distractor-005-2026-01-05", "Distractor 5", "HERR", "GUIA",
             "Configuración de herramienta legacy.", 24),
    _EvalDoc("TEC-distractor-006-2026-01-06", "Distractor 6", "TEC", "MTEC",
             "Documento técnico antiguo.", 25),
    _EvalDoc("PROC-distractor-007-2026-01-07", "Distractor 7", "PROC", "PROC",
             "Proceso obsoleto reemplazado.", 26),
    _EvalDoc("POL-distractor-008-2026-01-08", "Distractor 8", "PROC", "POL",
             "Política antigua superseded.", 27),
    _EvalDoc("ARQ-distractor-009-2026-01-09", "Distractor 9", "ARQ", "MTEC",
             "Patrón de diseño no aplicado.", 28),
    _EvalDoc("HERR-distractor-010-2026-01-10", "Distractor 10", "HERR", "GUIA",
             "Herramienta deprecated.", 29),
)

VECTOR_DIM: int = 1024


def _unit_vector(slot: int) -> list[float]:
    """Vector 1024-dim con 1.0 en la posición `slot`."""
    vec = [0.0] * VECTOR_DIM
    if 0 <= slot < VECTOR_DIM:
        vec[slot] = 1.0
    return vec


# ===========================================================================
# FakeEmbedder pre-cargado del eval set
# ===========================================================================


@dataclass
class _EvalEmbedder:
    """`EmbedderPort`-compatible. Mapea `query_text -> vector` según el
    `query_vector_seed` del eval set. Las queries multi-relevant generan
    combinación lineal normalizada de los slots de los docs relevantes
    para que la búsqueda recupere todos en el top-K.
    """

    query_map: dict[str, list[float]] = field(default_factory=dict)
    """`{query_text: vector_1024dim}`."""

    async def embed_documents(self, texts: Sequence[str]) -> EmbeddingBatch:  # noqa: ARG002
        raise NotImplementedError("eval no embedea docs — usa seed_data")

    async def embed_query(self, text: str) -> EmbeddingBatch:
        vector = self.query_map.get(text)
        if vector is None:
            # Vector cero para queries no registradas — devolverá scores
            # bajos. El test debería fallar limpio.
            vector = [0.0] * VECTOR_DIM
        return EmbeddingBatch(
            vectors=(tuple(vector),),
            input_tokens=len(text),
            cost_usd=0.0,
            model="fake-eval",
        )


def _build_query_vector(case: EvalCase, corpus_by_id: dict[str, _EvalDoc]) -> list[float]:
    """Vector de query = combinación normalizada de los slots de los
    docs `expected_relevant`. Si solo hay 1 relevante, el query vector
    es exacto a su slot (cosine match perfecto)."""
    slots = [
        corpus_by_id[doc_id].slot
        for doc_id in case.expected_relevant_doc_ids
        if doc_id in corpus_by_id
    ]
    if not slots:
        # Fallback: usar query_vector_seed como slot directo.
        slots = [int(case.query_vector_seed)]
    vec = [0.0] * VECTOR_DIM
    for slot in slots:
        if 0 <= slot < VECTOR_DIM:
            vec[slot] += 1.0
    # Normalizar para que tenga norma 1 (cosine consistente).
    norm = sum(x * x for x in vec) ** 0.5
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


# ===========================================================================
# Seed: limpia + inserta corpus
# ===========================================================================


async def _seed_data(session_factory) -> None:  # type: ignore[no-untyped-def]
    """Limpia + siembra el corpus del eval.

    Idempotente: borra cualquier doc del eval previo (por id exacto) y
    sus chunks via cascade — luego reinserta. Otros docs del usuario
    permanecen intactos.
    """
    from sqlalchemy import bindparam

    doc_ids = tuple(d.doc_id for d in EVAL_CORPUS)

    async with session_factory() as db:
        # Cascade borra los chunks asociados (FK ON DELETE CASCADE).
        stmt = text("DELETE FROM documents WHERE id IN :doc_ids").bindparams(
            bindparam("doc_ids", expanding=True)
        )
        await db.execute(stmt, {"doc_ids": list(doc_ids)})
        await db.commit()

    # Inserción.
    now = datetime.now(UTC)
    async with session_scope(session_factory) as db:
        for doc in EVAL_CORPUS:
            db.add(
                models.DocumentModel(
                    id=doc.doc_id,
                    titulo=doc.titulo,
                    carpeta=doc.carpeta,
                    tipo=doc.tipo,
                    autoritativo=False,
                    estado="vigente",
                    autor_oid=None,
                    autor_name="Eval Bot",
                    autor_role="QA",
                    fecha=now,
                    revision=now,
                    version="1.0",
                    citas=0,
                    score=0.0,
                    anonimizado=False,
                    fragmentos=1,
                    paginas=1,
                    formato="MD",
                    tags=[],
                    resumen=doc.content,
                )
            )

    chunk_repo = PostgresChunkRepository(session_factory)
    chunks: list[DocumentChunk] = []
    for doc in EVAL_CORPUS:
        chunks.append(
            DocumentChunk(
                id=f"chk-eval-{doc.slot:04d}-{uuid.uuid4().hex[:8]}",
                document_id=doc.doc_id,
                chunk_index=0,
                content=doc.content,
                embedding=_unit_vector(doc.slot),
                metadata={
                    "section_title": doc.titulo,
                    "strategy": "eval-seed",
                    "slot": doc.slot,
                },
            )
        )
    await chunk_repo.bulk_insert(chunks)


# ===========================================================================
# CLI
# ===========================================================================


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eval_rag",
        description="Eval determinista del pipeline RAG (recall@5 + precision@1).",
    )
    parser.add_argument(
        "--eval-set",
        type=Path,
        default=Path("tests/fixtures/eval_set.jsonl"),
        help="Path al JSONL del eval set.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help="Top-K para retrieval y para recall@k (default 5).",
    )
    parser.add_argument(
        "--seed-data",
        action="store_true",
        help="Pre-poblar la DB con el corpus de eval antes de correr.",
    )
    parser.add_argument(
        "--recall-threshold",
        type=float,
        default=DEFAULT_RECALL_THRESHOLD,
        help=f"Umbral de recall@k para considerar el eval exitoso (default {DEFAULT_RECALL_THRESHOLD}).",
    )
    parser.add_argument(
        "--precision-threshold",
        type=float,
        default=DEFAULT_PRECISION_THRESHOLD,
        help=f"Umbral de precision@1 (default {DEFAULT_PRECISION_THRESHOLD}).",
    )
    return parser


def _format_table(result: EvalResult) -> str:
    """Tabla por caso (TSV-like) para inspección manual / CI grep."""
    lines = [
        "query_id\tprecision@1\trecall@k\texpected_top\tactual_top",
    ]
    for case in result.cases:
        lines.append(
            f"{case.query_id}\t{case.precision_at_1:.2f}\t"
            f"{case.recall_at_k:.2f}\t{case.expected_top_doc_id}\t"
            f"{case.actual_top_doc_id or '<none>'}"
        )
    return "\n".join(lines)


def _format_summary(result: EvalResult, *, recall_th: float, precision_th: float) -> str:
    passed = meets_thresholds(
        result, recall_threshold=recall_th, precision_threshold=precision_th
    )
    return (
        f"cases={result.total_cases} "
        f"recall@{result.k}_avg={result.recall_at_k_avg:.4f} (umbral {recall_th:.2f}) "
        f"precision@1_avg={result.precision_at_1_avg:.4f} (umbral {precision_th:.2f}) "
        f"passed_recall={result.cases_passed_recall}/{result.total_cases} "
        f"passed_precision={result.cases_passed_precision}/{result.total_cases} "
        f"PASS" if passed else
        f"cases={result.total_cases} "
        f"recall@{result.k}_avg={result.recall_at_k_avg:.4f} (umbral {recall_th:.2f}) "
        f"precision@1_avg={result.precision_at_1_avg:.4f} (umbral {precision_th:.2f}) "
        f"passed_recall={result.cases_passed_recall}/{result.total_cases} "
        f"passed_precision={result.cases_passed_precision}/{result.total_cases} "
        f"FAIL"
    )


async def _run(args: argparse.Namespace, settings: Settings) -> EvalResult:
    if settings.database_url is None:
        raise ExternalServiceError(
            "SQA_KB_DATABASE_URL es obligatoria.", service="postgres"
        )

    cases = load_eval_set(args.eval_set)
    if not cases:
        raise ValueError(f"El eval set en {args.eval_set} está vacío.")

    engine = create_engine(settings)
    factory = create_session_factory(engine)
    corpus_by_id = {d.doc_id: d for d in EVAL_CORPUS}
    try:
        if args.seed_data:
            await _seed_data(factory)

        # Construir el FakeEmbedder pre-cargado.
        query_map = {
            case.query_text: _build_query_vector(case, corpus_by_id) for case in cases
        }
        embedder = _EvalEmbedder(query_map=query_map)
        searcher = HybridSearcher(embedder=embedder, session_factory=factory)

        async def _search_fn(case: EvalCase) -> Sequence[HybridChunk]:
            return await searcher.search(case.query_text, top_k=args.top_k)

        return await run_eval(cases, search_fn=_search_fn, k=args.top_k)
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    settings = get_settings()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        result = asyncio.run(_run(args, settings))
    except ExternalServiceError as exc:
        logger.error("eval_aborted: %s", exc)
        return 2
    except Exception as exc:  # noqa: BLE001
        logger.exception("eval_crashed: %s", exc)
        return 3

    print(_format_table(result))  # noqa: T201
    print("---")  # noqa: T201
    print(_format_summary(  # noqa: T201
        result,
        recall_th=args.recall_threshold,
        precision_th=args.precision_threshold,
    ))

    passed = meets_thresholds(
        result,
        recall_threshold=args.recall_threshold,
        precision_threshold=args.precision_threshold,
    )
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

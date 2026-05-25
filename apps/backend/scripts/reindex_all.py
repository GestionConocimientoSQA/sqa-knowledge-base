"""CLI thin para reindexar el corpus (Fase 3.6).

Toda la lógica vive en `sqa_kb.rag.reindex` — este script solo parsea
args, cablea adapters reales (PostgreSQL + Cohere) e imprime stats.

Uso típico:

    # Reindex completo
    python scripts/reindex_all.py

    # Solo una carpeta
    python scripts/reindex_all.py --carpeta TEC

    # Filtro combinado
    python scripts/reindex_all.py --carpeta TEC --tipo POL

    # Dry run para ver cuántos docs procesaría sin tocar el indexer
    python scripts/reindex_all.py --dry-run

    # Lote chico (debugging)
    python scripts/reindex_all.py --batch-size 10

Requisitos al runtime:
- `SQA_KB_DATABASE_URL` apuntando a un Postgres con las migraciones
  Alembic aplicadas (incluido el índice HNSW de Fase 3.3).
- `SQA_KB_COHERE_API_KEY` con una key válida (no se mockea acá —
  los tests del módulo `reindex.py` usan fake embedder).
- Las extensiones `pgvector` + `pg_trgm` en la DB.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from sqa_kb.adapters.embeddings.cohere import CohereEmbedder
from sqa_kb.adapters.repositories.postgres import create_engine, create_session_factory
from sqa_kb.adapters.repositories.postgres.chunks import PostgresChunkRepository
from sqa_kb.adapters.repositories.postgres.documents import PostgresDocumentRepository
from sqa_kb.config import Settings, get_settings
from sqa_kb.domain.errors import ExternalServiceError
from sqa_kb.domain.value_objects import CategoryCode, DocTypeCode
from sqa_kb.observability.logging import configure_logging, get_logger
from sqa_kb.rag.indexer import Indexer
from sqa_kb.rag.reindex import DEFAULT_BATCH_SIZE, ReindexStats, reindex

logger = get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reindex_all",
        description="Reindex batch del KB sobre `document_chunks`.",
    )
    parser.add_argument(
        "--carpeta",
        action="append",
        default=None,
        choices=[c.value for c in CategoryCode],
        help="Filtra por carpeta (puede repetirse: --carpeta TEC --carpeta ARQ).",
    )
    parser.add_argument(
        "--tipo",
        action="append",
        default=None,
        choices=[t.value for t in DocTypeCode],
        help="Filtra por tipo de documento (puede repetirse).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Tamaño de página (default {DEFAULT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No llama al indexer — solo cuenta cuántos docs procesaría.",
    )
    return parser


def _format_stats(stats: ReindexStats) -> str:
    """Pretty-print de las stats. Estable para grep en CI."""
    return (
        f"docs_processed={stats.docs_processed} "
        f"docs_indexed={stats.docs_indexed} "
        f"docs_skipped={stats.docs_skipped} "
        f"docs_failed={stats.docs_failed} "
        f"chunks_created={stats.chunks_created} "
        f"tokens={stats.tokens_embedded} "
        f"cost_usd={stats.cost_usd}"
    )


async def _run(args: argparse.Namespace, settings: Settings) -> ReindexStats:
    if settings.database_url is None:
        raise ExternalServiceError(
            "SQA_KB_DATABASE_URL es obligatoria — no se puede correr el reindex.",
            service="postgres",
        )
    if settings.cohere_api_key is None and not args.dry_run:
        raise ExternalServiceError(
            "SQA_KB_COHERE_API_KEY es obligatoria fuera de --dry-run.",
            service="cohere",
        )

    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        document_repo = PostgresDocumentRepository(factory)
        chunk_repo = PostgresChunkRepository(factory)
        # En --dry-run nunca llamamos al embedder, pero el Indexer lo
        # exige por construcción. Pasamos uno con key vacía — fallaría
        # a la primera llamada pero el dry-run no llega ahí.
        embedder_key = (
            settings.cohere_api_key.get_secret_value()
            if settings.cohere_api_key is not None
            else "dry-run-no-key"
        )
        embedder = CohereEmbedder(
            api_key=embedder_key,
            model=settings.cohere_embed_model,
        )
        indexer = Indexer(
            embedder=embedder,
            chunk_repo=chunk_repo,
            document_repo=document_repo,
        )

        carpetas = [CategoryCode(c) for c in args.carpeta] if args.carpeta else None
        tipos = [DocTypeCode(t) for t in args.tipo] if args.tipo else None

        async def _on_page(progress: ReindexStats) -> None:
            logger.info("reindex_progress", **_stats_dict(progress))

        return await reindex(
            document_repo=document_repo,
            indexer=indexer,
            carpetas=carpetas,
            tipos=tipos,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            progress_callback=_on_page,
        )
    finally:
        await engine.dispose()


def _stats_dict(stats: ReindexStats) -> dict[str, object]:
    """Convierte stats a dict para structlog (kwargs estructurados)."""
    return {
        "docs_processed": stats.docs_processed,
        "docs_indexed": stats.docs_indexed,
        "docs_skipped": stats.docs_skipped,
        "docs_failed": stats.docs_failed,
        "chunks_created": stats.chunks_created,
        "tokens": stats.tokens_embedded,
        "cost_usd": stats.cost_usd,
    }


def main(argv: list[str] | None = None) -> int:
    """Entrypoint del CLI. Devuelve exit code (0 OK, 1 si hubo errores)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(settings)

    try:
        stats = asyncio.run(_run(args, settings))
    except ExternalServiceError as exc:
        logger.error("reindex_aborted", reason=str(exc))
        return 2
    except Exception as exc:  # noqa: BLE001
        logger.exception("reindex_crashed: %s", exc)
        return 3

    logger.info("reindex_finished", **_stats_dict(stats))
    print(_format_stats(stats))  # stdout para scripts que capturan el output  # noqa: T201
    return 1 if stats.has_errors else 0


if __name__ == "__main__":
    sys.exit(main())

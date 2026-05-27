"""Tests del worker ingestion_processor (Fase 4.6).

Verifican el wrapper `process_ingestion_background`: dispara classify y
swallowea excepciones (no las propaga, las loggea).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqa_kb.domain.entities import IngestionItem
from sqa_kb.domain.value_objects import IngestionStatus
from sqa_kb.services.ingestion_service import process_ingestion_background


def _item(status=IngestionStatus.EN_REVISION) -> IngestionItem:  # type: ignore[no-untyped-def]
    return IngestionItem(
        id="ing-1",
        filename="x.docx",
        size_bytes=10,
        status=status,
        uploaded_by_oid="o",
        uploaded_at=datetime.now(UTC),
        blob_path="ing-1/x.docx",
    )


@dataclass
class _FakeService:
    classify_calls: list[str] = field(default_factory=list)
    raise_on_classify: bool = False

    async def classify(self, item_id: str) -> IngestionItem:
        self.classify_calls.append(item_id)
        if self.raise_on_classify:
            raise RuntimeError("classify exploded")
        return _item()


async def test_worker_calls_classify(caplog: Any) -> None:
    svc = _FakeService()
    with caplog.at_level(logging.INFO):
        await process_ingestion_background(svc, "ing-1")  # type: ignore[arg-type]
    assert svc.classify_calls == ["ing-1"]
    assert any("ingestion_autoclassified" in r.message for r in caplog.records)


async def test_worker_swallows_exceptions(caplog: Any) -> None:
    """Si classify rota, el worker NO propaga — loggea y termina."""
    svc = _FakeService(raise_on_classify=True)
    with caplog.at_level(logging.ERROR):
        # No debe levantar.
        await process_ingestion_background(svc, "ing-1")  # type: ignore[arg-type]
    assert any("ingestion_autoclassify_failed" in r.message for r in caplog.records)

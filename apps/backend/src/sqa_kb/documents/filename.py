"""Filename builder — convención de nombres del KB (Fase 4.5).

Formato: `[TIPO]-[tema-slug]-[YYYY-MM-DD].ext`
Ejemplo: `MTEC-flaky-tests-en-ci-2026-05-26.docx`

Reutiliza la misma lógica de slug del agente (`build_document_id`) para
que el ID lógico del documento y el nombre del archivo sean coherentes.
La diferencia es que el filename agrega la extensión del formato.
"""

from __future__ import annotations

from datetime import datetime

from sqa_kb.agent.markdown_generator import build_document_id


def build_filename(
    *,
    document_type: str,
    topic: str,
    fecha: datetime,
    extension: str,
) -> str:
    """Devuelve `[TIPO]-[tema]-[YYYY-MM-DD].ext`.

    `extension` se normaliza: se le quita el punto inicial si lo trae y
    se pasa a minúsculas (`.DOCX` → `docx`).
    """
    ext = extension.lower().lstrip(".")
    base = build_document_id(document_type=document_type, topic=topic, fecha=fecha)
    return f"{base}.{ext}" if ext else base

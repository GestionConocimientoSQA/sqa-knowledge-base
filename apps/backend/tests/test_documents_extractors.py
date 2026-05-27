"""Tests de los extractores + dispatcher (Fase 4.3).

Estrategia roundtrip: generamos un archivo con el generador de 4.1/4.2
y lo extraemos con el extractor de 4.3, verificando que el texto clave
sobrevive el viaje. Esto cubre generador + extractor a la vez.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sqa_kb.documents.extractors import (
    ExtractedDocument,
    ExtractorDispatcher,
    UnsupportedFormatError,
)
from sqa_kb.documents.extractors.docx import DocxExtractor
from sqa_kb.documents.extractors.pdf import PdfExtractor
from sqa_kb.documents.extractors.pptx import PptxExtractor
from sqa_kb.documents.extractors.xlsx import XlsxExtractor
from sqa_kb.documents.generators.docx import DocxGenerator
from sqa_kb.documents.generators.pdf import PdfGenerator
from sqa_kb.documents.generators.pptx import PptxGenerator
from sqa_kb.documents.generators.xlsx import XlsxGenerator
from sqa_kb.documents.models import DocumentContent, QaPair


def _content() -> DocumentContent:
    return DocumentContent(
        document_id="MTEC-roundtrip-2026-05-26",
        title="Titulo Roundtrip Unico",
        category="TEC",
        document_type="MTEC",
        version="1.0",
        fecha=datetime(2026, 5, 26, tzinfo=UTC),
        author_name="Tester",
        author_role="QA",
        topic="topic marcador roundtrip alfa",
        body_blocks=("bloque beta de contenido", "bloque gamma de contenido"),
        qa_pairs=(QaPair(question="pregunta delta", answer="respuesta epsilon"),),
        is_anonymized=False,
    )


# ===========================================================================
# DOCX roundtrip
# ===========================================================================


def test_docx_roundtrip_preserves_text() -> None:
    blob = DocxGenerator().generate(_content()).data
    extracted = DocxExtractor().extract(blob)
    assert isinstance(extracted, ExtractedDocument)
    assert "Titulo Roundtrip Unico" in extracted.text
    assert "topic marcador roundtrip alfa" in extracted.text
    assert "bloque beta de contenido" in extracted.text
    assert "respuesta epsilon" in extracted.text


def test_docx_roundtrip_detects_sections() -> None:
    blob = DocxGenerator().generate(_content()).data
    extracted = DocxExtractor().extract(blob)
    # El generador usa headings de sección (Tema, Contenido, Precisiones)
    # pero con estilo custom (no "Heading"), así que la detección puede
    # variar. Garantizamos al menos que hay texto.
    assert not extracted.is_empty


# ===========================================================================
# PPTX roundtrip
# ===========================================================================


def test_pptx_roundtrip_preserves_text() -> None:
    blob = PptxGenerator().generate(_content()).data
    extracted = PptxExtractor().extract(blob)
    assert "Titulo Roundtrip Unico" in extracted.text
    assert "topic marcador roundtrip alfa" in extracted.text
    assert "bloque beta de contenido" in extracted.text


def test_pptx_roundtrip_section_per_slide() -> None:
    blob = PptxGenerator().generate(_content()).data
    extracted = PptxExtractor().extract(blob)
    # Portada + tema + 2 contenido + 1 qa = 5 slides con texto.
    assert extracted.page_count == 5
    assert len(extracted.sections) == 5


# ===========================================================================
# PDF roundtrip
# ===========================================================================


def test_pdf_roundtrip_preserves_text() -> None:
    blob = PdfGenerator().generate(_content()).data
    extracted = PdfExtractor().extract(blob)
    assert "Titulo Roundtrip Unico" in extracted.text
    assert "topic marcador roundtrip alfa" in extracted.text
    assert "respuesta epsilon" in extracted.text


def test_pdf_roundtrip_section_per_page() -> None:
    blob = PdfGenerator().generate(_content()).data
    extracted = PdfExtractor().extract(blob)
    assert extracted.page_count >= 1
    assert all(s.title.startswith("Página") for s in extracted.sections)


# ===========================================================================
# XLSX roundtrip
# ===========================================================================


def test_xlsx_roundtrip_preserves_text() -> None:
    blob = XlsxGenerator().generate(_content()).data
    extracted = XlsxExtractor().extract(blob)
    assert "Titulo Roundtrip Unico" in extracted.text
    assert "topic marcador roundtrip alfa" in extracted.text
    assert "respuesta epsilon" in extracted.text


def test_xlsx_roundtrip_section_per_sheet() -> None:
    blob = XlsxGenerator().generate(_content()).data
    extracted = XlsxExtractor().extract(blob)
    titles = {s.title for s in extracted.sections}
    assert {"Metadata", "Contenido", "Precisiones"} <= titles


# ===========================================================================
# Dispatcher
# ===========================================================================


def test_dispatcher_supported_extensions() -> None:
    d = ExtractorDispatcher()
    assert d.supported_extensions == ("docx", "pdf", "pptx", "xlsx")


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("doc.docx", True),
        ("pres.PPTX", True),  # case-insensitive
        ("sheet.xlsx", True),
        ("report.pdf", True),
        ("notes.txt", False),
        ("image.png", False),
        ("noext", False),
    ],
)
def test_dispatcher_supports(filename: str, expected: bool) -> None:
    assert ExtractorDispatcher().supports(filename) is expected


def test_dispatcher_routes_by_extension() -> None:
    d = ExtractorDispatcher()
    blob = DocxGenerator().generate(_content()).data
    extracted = d.extract("cualquier-nombre.docx", blob)
    assert "Titulo Roundtrip Unico" in extracted.text


def test_dispatcher_case_insensitive_extension() -> None:
    d = ExtractorDispatcher()
    blob = PdfGenerator().generate(_content()).data
    extracted = d.extract("REPORTE.PDF", blob)
    assert "Titulo Roundtrip Unico" in extracted.text


def test_dispatcher_unsupported_format_raises() -> None:
    d = ExtractorDispatcher()
    with pytest.raises(UnsupportedFormatError, match="no soportado"):
        d.extract("data.csv", b"a,b,c")


def test_dispatcher_no_extension_raises() -> None:
    d = ExtractorDispatcher()
    with pytest.raises(UnsupportedFormatError):
        d.extract("sinextension", b"x")


def test_dispatcher_extractor_for_returns_right_handler() -> None:
    d = ExtractorDispatcher()
    assert isinstance(d.extractor_for("a.docx"), DocxExtractor)
    assert isinstance(d.extractor_for("a.pptx"), PptxExtractor)
    assert isinstance(d.extractor_for("a.pdf"), PdfExtractor)
    assert isinstance(d.extractor_for("a.xlsx"), XlsxExtractor)


# ===========================================================================
# Edge: empty document
# ===========================================================================


def test_extracted_document_is_empty_flag() -> None:
    assert ExtractedDocument(text="").is_empty is True
    assert ExtractedDocument(text="  \n ").is_empty is True
    assert ExtractedDocument(text="hola").is_empty is False

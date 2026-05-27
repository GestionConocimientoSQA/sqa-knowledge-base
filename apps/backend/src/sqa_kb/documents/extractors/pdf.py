"""PdfExtractor — lee texto de un `.pdf` (Fase 4.3).

Usa pdfplumber. Cada página es una `ExtractedSection` (`title="Página N"`,
`content` = texto de la página). PDF rara vez expone estructura semántica
de headings, así que no intentamos inferirla — el chunker hace fallback a
estrategia semántica sobre `text`.
"""

from __future__ import annotations

import io

import pdfplumber

from sqa_kb.documents.extractors.base import ExtractedDocument, ExtractedSection

EXTENSIONS = ("pdf",)


class PdfExtractor:
    """Implementa `DocumentExtractor` para `.pdf`."""

    @property
    def extensions(self) -> tuple[str, ...]:
        return EXTENSIONS

    def extract(self, data: bytes) -> ExtractedDocument:
        sections: list[ExtractedSection] = []
        all_text: list[str] = []

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            page_count = len(pdf.pages)
            for idx, page in enumerate(pdf.pages, start=1):
                page_text = (page.extract_text() or "").strip()
                if not page_text:
                    continue
                sections.append(
                    ExtractedSection(title=f"Página {idx}", content=page_text)
                )
                all_text.append(page_text)

        return ExtractedDocument(
            text="\n".join(all_text).strip(),
            sections=tuple(sections),
            page_count=page_count,
        )

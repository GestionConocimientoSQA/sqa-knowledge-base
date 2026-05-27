"""PdfGenerator — PDF con branding SQA vía reportlab (Fase 4.2).

Genera el PDF **desde cero** con reportlab (no convierte desde DOCX),
según la decisión de Fase 4: sin dependencias externas (LibreOffice /
Gotenberg). La estructura es la misma de los demás formatos:
título + barra naranja → tabla de metadata → Tema → Contenido →
Precisiones → footer con número de página.

Si TI más adelante prefiere DOCX→PDF idéntico vía LibreOffice headless,
se implementa otro `PdfGenerator` con la misma interfaz (Port) y se
cambia el wiring.
"""

from __future__ import annotations

import io

from reportlab.lib.colors import Color
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from sqa_kb.documents import branding
from sqa_kb.documents.branding import RgbColor
from sqa_kb.documents.doc_types import category_label, doc_type_label
from sqa_kb.documents.generators.base import GeneratedFile
from sqa_kb.documents.models import DocumentContent

MEDIA_TYPE = "application/pdf"
EXTENSION = "pdf"


def _color(c: RgbColor) -> Color:
    r, g, b = c.rgb_tuple
    return Color(r / 255, g / 255, b / 255)


class PdfGenerator:
    """Genera `.pdf` con branding SQA. Implementa `DocumentGenerator`."""

    @property
    def extension(self) -> str:
        return EXTENSION

    @property
    def media_type(self) -> str:
        return MEDIA_TYPE

    def generate(self, content: DocumentContent) -> GeneratedFile:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            title=content.title,
            author=content.author_name,
        )
        styles = self._styles()
        story = []

        # Caption + título + barra naranja.
        tipo = doc_type_label(content.document_type)
        carpeta = category_label(content.category)
        story.append(Paragraph(f"{tipo} &nbsp;·&nbsp; {carpeta}".upper(), styles["caption"]))
        story.append(Paragraph(content.title, styles["doc_title"]))
        story.append(
            HRFlowable(
                width="40%",
                thickness=3,
                color=_color(branding.COLOR_ACENTO),
                spaceBefore=2,
                spaceAfter=10,
                hAlign="LEFT",
            )
        )

        # Tabla de metadata.
        story.append(self._metadata_table(content, styles))
        story.append(Spacer(1, 8 * mm))

        # Tema.
        story.append(Paragraph("Tema", styles["section"]))
        story.append(Paragraph(_escape(content.topic), styles["body"]))

        # Contenido.
        if content.body_blocks:
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph("Contenido", styles["section"]))
            for block in content.body_blocks:
                story.append(Paragraph(_escape(block), styles["body"]))

        # Precisiones.
        if content.qa_pairs:
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph("Precisiones", styles["section"]))
            for qa in content.qa_pairs:
                story.append(Paragraph(_escape(qa.question), styles["question"]))
                story.append(Paragraph(_escape(qa.answer), styles["body"]))

        doc.build(
            story,
            onFirstPage=self._footer,
            onLaterPages=self._footer,
        )
        return GeneratedFile(
            filename=f"{content.document_id}.{EXTENSION}",
            media_type=MEDIA_TYPE,
            data=buffer.getvalue(),
        )

    # -- estilos ------------------------------------------------------------

    def _styles(self) -> dict[str, ParagraphStyle]:
        base = getSampleStyleSheet()
        return {
            "caption": ParagraphStyle(
                "sqa_caption",
                parent=base["Normal"],
                fontSize=branding.SIZE_CAPTION,
                textColor=_color(branding.COLOR_TEXTO_SECUNDARIO),
                spaceAfter=2,
            ),
            "doc_title": ParagraphStyle(
                "sqa_title",
                parent=base["Title"],
                fontSize=branding.SIZE_PORTADA_TITULO - 6,
                textColor=_color(branding.COLOR_TITULO),
                alignment=TA_LEFT,
                spaceAfter=2,
            ),
            "section": ParagraphStyle(
                "sqa_section",
                parent=base["Heading2"],
                fontSize=branding.SIZE_H2,
                textColor=_color(branding.COLOR_SUBTITULO),
                spaceBefore=6,
                spaceAfter=4,
            ),
            "body": ParagraphStyle(
                "sqa_body",
                parent=base["Normal"],
                fontSize=branding.SIZE_BODY,
                textColor=_color(branding.COLOR_CUERPO),
                spaceAfter=4,
                leading=15,
            ),
            "question": ParagraphStyle(
                "sqa_question",
                parent=base["Normal"],
                fontSize=branding.SIZE_BODY,
                textColor=_color(branding.COLOR_CUERPO),
                fontName="Helvetica-Bold",
                spaceBefore=4,
            ),
        }

    def _metadata_table(self, content: DocumentContent, styles) -> Table:  # type: ignore[no-untyped-def]
        autor = content.author_name
        if content.author_role:
            autor = f"{content.author_name} ({content.author_role})"
        data = [
            ["Carpeta", f"{content.category} — {category_label(content.category)}"],
            ["Tipo", f"{content.document_type} — {doc_type_label(content.document_type)}"],
            ["Versión", content.version],
            ["Fecha", content.fecha.strftime("%Y-%m-%d")],
            ["Autor", autor],
        ]
        if content.is_anonymized:
            data.append(["Anonimizado", "Sí"])

        table = Table(data, colWidths=[35 * mm, 130 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), _color(branding.COLOR_FONDO_TABLA_HEADER)),
                    ("TEXTCOLOR", (0, 0), (0, -1), _color(branding.BLANCO)),
                    ("TEXTCOLOR", (1, 0), (1, -1), _color(branding.COLOR_CUERPO)),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), branding.SIZE_BODY),
                    ("GRID", (0, 0), (-1, -1), 0.5, _color(branding.GRIS_TEXTO)),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return table

    # -- footer con número de página ----------------------------------------

    def _footer(self, canvas, doc) -> None:  # type: ignore[no-untyped-def]
        canvas.saveState()
        canvas.setFont("Helvetica", branding.SIZE_FOOTER)
        canvas.setFillColor(_color(branding.COLOR_TEXTO_SECUNDARIO))
        canvas.drawString(20 * mm, 12 * mm, branding.DOC_FOOTER_LEFT)
        canvas.drawRightString(
            A4[0] - 20 * mm, 12 * mm, f"Página {doc.page}"
        )
        canvas.restoreState()


def _escape(text: str) -> str:
    """Escapa caracteres especiales de los mini-tags de reportlab Paragraph
    (`<`, `>`, `&`) para que el texto del usuario no rompa el parser."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

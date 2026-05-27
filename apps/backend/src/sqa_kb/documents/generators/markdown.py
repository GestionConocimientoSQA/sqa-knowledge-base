"""MarkdownGenerator — formato canónico de texto (Fase 4.1).

Produce el mismo Markdown que el agente generaba desde Fase 2.4, pero
desde el DTO `DocumentContent` (no desde `AgentState`). El módulo
`agent/markdown_generator.py` delega acá para no duplicar la estructura.

La estructura es la del template `markdown_document.j2`:
título → tabla de metadata → Tema → Contenido → Precisiones.
"""

from __future__ import annotations

from sqa_kb.documents.doc_types import category_label, doc_type_label
from sqa_kb.documents.generators.base import GeneratedFile
from sqa_kb.documents.models import DocumentContent

MEDIA_TYPE = "text/markdown; charset=utf-8"
EXTENSION = "md"


class MarkdownGenerator:
    """Genera Markdown UTF-8. Implementa `DocumentGenerator`."""

    @property
    def extension(self) -> str:
        return EXTENSION

    @property
    def media_type(self) -> str:
        return MEDIA_TYPE

    def generate(self, content: DocumentContent) -> GeneratedFile:
        markdown = self.render(content)
        return GeneratedFile(
            filename=f"{content.document_id}.{EXTENSION}",
            media_type=MEDIA_TYPE,
            data=markdown.encode("utf-8"),
        )

    def render(self, content: DocumentContent) -> str:
        """Devuelve el Markdown como string (útil para el agente que
        persiste `content` como texto, no como bytes)."""
        lines: list[str] = [f"# {content.title}", ""]

        # Tabla de metadata.
        autor = content.author_name
        if content.author_role:
            autor = f"{content.author_name} ({content.author_role})"
        lines += [
            "| Metadata | Valor |",
            "|----------|-------|",
            f"| Carpeta | {content.category} — {category_label(content.category)} |",
            f"| Tipo | {content.document_type} — {doc_type_label(content.document_type)} |",
            f"| Versión | {content.version} |",
            f"| Fecha | {content.fecha.strftime('%Y-%m-%d')} |",
            f"| Autor | {autor} |",
        ]
        if content.is_anonymized:
            lines.append("| Anonimizado | Sí |")
        lines.append("")

        # Tema.
        lines += ["## Tema", "", content.topic, ""]

        # Contenido.
        if content.body_blocks:
            lines += ["## Contenido", ""]
            for block in content.body_blocks:
                lines += [block, ""]

        # Precisiones (deep-dive).
        if content.qa_pairs:
            lines += ["## Precisiones", ""]
            for qa in content.qa_pairs:
                lines += [f"**{qa.question}**", "", qa.answer, ""]

        # Newline final consistente.
        return "\n".join(lines).rstrip() + "\n"

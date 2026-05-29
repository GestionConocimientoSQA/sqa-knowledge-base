"""MarkdownExtractor — lee `.md` (Fase 9.5).

Los archivos `.md` generados por `DocumentationSessionService` entran al
pipeline de ingesta. El extractor parsea frontmatter YAML opcional + el
cuerpo, y crea secciones desde los headings `##` para que el chunker no
necesite hacer fallback semántico.

Markdown es el formato preferido del agente (todas las generaciones
internas son `.md`), así que ahora que los humanos también pueden subir
markdown a la cola, soportarlo nativamente es consistente.
"""

from __future__ import annotations

import re

from sqa_kb.documents.extractors.base import ExtractedDocument, ExtractedSection

EXTENSIONS = ("md", "markdown")

_FRONTMATTER_RE = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL
)
_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


class MarkdownExtractor:
    """Implementa `DocumentExtractor` para `.md` / `.markdown`."""

    @property
    def extensions(self) -> tuple[str, ...]:
        return EXTENSIONS

    def extract(self, data: bytes) -> ExtractedDocument:
        text = data.decode("utf-8", errors="replace")

        # Strip frontmatter YAML si está presente (no se incluye en el
        # body extraído — vive como metadata fuera del texto).
        match = _FRONTMATTER_RE.match(text)
        body = match.group(2) if match else text

        sections = self._extract_sections(body)
        # `page_count = 1` por convención (markdown no tiene paginación).
        return ExtractedDocument(
            text=body.strip(),
            sections=tuple(sections),
            page_count=1,
        )

    @staticmethod
    def _extract_sections(body: str) -> list[ExtractedSection]:
        """Divide el body por headings `##` (sección de nivel 2)."""
        sections: list[ExtractedSection] = []
        # Localizamos cada `##` y partimos.
        matches = list(_H2_RE.finditer(body))
        if not matches:
            # Sin headings: el body entero queda como una sección "Cuerpo".
            stripped = body.strip()
            if stripped:
                sections.append(ExtractedSection(title="Cuerpo", content=stripped))
            return sections
        for i, m in enumerate(matches):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            content = body[start:end].strip()
            sections.append(
                ExtractedSection(title=m.group(1).strip(), content=content)
            )
        return sections

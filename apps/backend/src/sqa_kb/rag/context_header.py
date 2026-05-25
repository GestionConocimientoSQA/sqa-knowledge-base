"""Helper para construir el header contextual prefijado a cada chunk.

El header **NO se almacena** en `document_chunks.content` — solo se usa
para generar el embedding del chunk. Mejora la calidad del retrieval
porque el modelo "ve" la metadata estructural junto al texto.

Formato (espejo del ROADMAP §17.2):

    [Tipo: <human-readable> | Carpeta: <CODE> | Sección: <title>]

    <chunk content>

Si falta `section_title`, el header omite el segmento "Sección:".
"""

from __future__ import annotations

# Mapeo de códigos de tipo → nombre humano usado en el header.
# Lo mantenemos acá (no en value_objects) porque es solo para el prompt
# de embeddings — el dominio sigue manejando los códigos cortos.
_TYPE_HUMAN_NAMES: dict[str, str] = {
    "POL": "Política",
    "PROC": "Procedimiento",
    "GUIA": "Guía",
    "INST": "Instructivo",
    "SERV": "Servicio",
    "MTEC": "Memoria Técnica",
    "ACEL": "Acelerador",
    "UEN": "Unidad de Negocio",
    "ARCL": "Arquetipo de Cliente",
    "FORM": "Formato",
    "PRES": "Presentación",
}


def format_context_header(
    *,
    document_type: str,
    category: str,
    section_title: str | None = None,
    content: str,
) -> str:
    """Construye el texto que se le pasa al embedder.

    `document_type` viene como código (`MTEC`, `POL`, ...) y lo
    traducimos a nombre humano. Si el código es desconocido (extensión
    futura), usamos el código tal cual — es defensivo, no preferimos
    fallar el indexer por un tipo nuevo.

    `category` se deja como código (`TEC`, `ARQ`) porque es corto y
    visible en cualquier idioma.
    """
    type_name = _TYPE_HUMAN_NAMES.get(document_type, document_type)
    header_parts = [f"Tipo: {type_name}", f"Carpeta: {category}"]
    if section_title and section_title.strip():
        header_parts.append(f"Sección: {section_title.strip()}")
    header = "[" + " | ".join(header_parts) + "]"
    return f"{header}\n\n{content}"


def type_human_name(document_type: str) -> str:
    """Expone el mapping para tests / logs / debug."""
    return _TYPE_HUMAN_NAMES.get(document_type, document_type)

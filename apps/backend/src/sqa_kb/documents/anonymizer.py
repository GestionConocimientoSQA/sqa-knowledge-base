"""Anonimizador de PII (Fase 4.4).

Implementa el puerto `PiiFilter` (`ports/gateways.py`) con reglas regex
configurables. Reemplaza elementos identificables del cliente por
marcadores genéricos antes de indexar o exponer contenido.

Alcance Fase 4: regex. La interfaz `PiiFilter` queda lista para swap a
**Presidio** (lib de Microsoft, alineación con TI según
`docs/alineacion-arquitectura-ti.md §2.4`) cuando TI lo confirme — solo
cambia la implementación, no el contrato ni los callers.

Reglas default (LATAM + genéricas):
- Email
- Teléfono (formatos comunes con/sin código de país)
- IPv4
- Tarjeta de crédito (13-16 dígitos, con o sin separadores)
- NIT / cédula Colombia (secuencias de 8-10 dígitos con separadores de miles)
- URL con credenciales embebidas (`user:pass@host`)

Diseño:
- Cada `PiiRule` es `(name, pattern, replacement)`. La lista es
  inyectable — un caller puede pasar reglas custom o desactivar algunas.
- `anonymize` es async para cumplir el Protocol (aunque la regex es
  síncrona) — así el swap a Presidio (que puede hacer I/O a un endpoint)
  no cambia la firma.
- Las reglas se aplican en orden; el orden importa (p. ej. tarjeta antes
  que teléfono para no fragmentar números largos).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from sqa_kb.ports.gateways import PiiFilterResult


@dataclass(frozen=True, slots=True)
class PiiRule:
    """Una regla de anonimización: patrón → marcador."""

    name: str
    pattern: re.Pattern[str]
    replacement: str


def _rule(name: str, regex: str, replacement: str, *, flags: int = 0) -> PiiRule:
    return PiiRule(name=name, pattern=re.compile(regex, flags), replacement=replacement)


# Orden IMPORTANTE: patrones más específicos / largos primero para que no
# sean fragmentados por reglas más cortas (p. ej. tarjeta antes que NIT).
DEFAULT_RULES: tuple[PiiRule, ...] = (
    # URL con credenciales ANTES que email: el `user:pass@host` de una
    # connection string contiene un patrón que la regla de email tomaría
    # como dirección si corriera primero.
    _rule(
        "url_credentials",
        r"\b[a-zA-Z][a-zA-Z0-9+.\-]*://[^\s:/@]+:[^\s:/@]+@[^\s/]+",
        "[URL_CON_CREDENCIALES]",
    ),
    _rule(
        "email",
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        "[EMAIL]",
    ),
    _rule(
        "credit_card",
        r"\b(?:\d[ \-]?){13,16}\b",
        "[TARJETA]",
    ),
    _rule(
        "ipv4",
        r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b",
        "[IP]",
    ),
    _rule(
        # Teléfono: opcional +código, separadores espacio/guion/paréntesis,
        # 7-11 dígitos en total. Requiere al menos 7 dígitos para no pisar
        # números cortos legítimos.
        "telefono",
        r"(?<!\d)(?:\+?\d{1,3}[ \-]?)?(?:\(\d{1,4}\)[ \-]?)?\d{3}[ \-]?\d{2,4}[ \-]?\d{2,4}(?!\d)",
        "[TELEFONO]",
    ),
    _rule(
        # NIT / cédula con separadores de miles (123.456.789 / 1.234.567).
        "id_nacional",
        r"\b\d{1,3}(?:\.\d{3}){2,3}(?:-\d)?\b",
        "[ID]",
    ),
)


class RegexAnonymizer:
    """Anonimizador basado en regex. Implementa el puerto `PiiFilter`.

    `enabled=False` lo convierte en no-op (devuelve el texto intacto),
    útil para entornos donde no se quiere anonimizar (p. ej. contenido
    ya curado). Espejo del comportamiento `presidio_enabled=False` del
    puerto.
    """

    def __init__(
        self,
        *,
        rules: Sequence[PiiRule] | None = None,
        enabled: bool = True,
    ) -> None:
        self._rules: tuple[PiiRule, ...] = tuple(rules) if rules is not None else DEFAULT_RULES
        self._enabled = enabled

    async def anonymize(self, text: str) -> PiiFilterResult:
        """Aplica las reglas en orden y devuelve texto + cantidad de
        reemplazos. No muta el input."""
        if not self._enabled or not text:
            return PiiFilterResult(text=text, replacements=0)

        result = text
        total = 0
        for rule in self._rules:
            result, count = rule.pattern.subn(rule.replacement, result)
            total += count
        return PiiFilterResult(text=result, replacements=total)

    def detect(self, text: str) -> dict[str, int]:
        """Devuelve `{nombre_regla: cantidad}` de matches SIN reemplazar.

        Útil para auditar qué PII hay en un texto antes de decidir
        anonimizar (p. ej. en el preview de ingesta del frontend)."""
        counts: dict[str, int] = {}
        for rule in self._rules:
            found = len(rule.pattern.findall(text))
            if found:
                counts[rule.name] = found
        return counts


class NoopAnonymizer:
    """No-op explícito que cumple el puerto `PiiFilter` — devuelve el
    texto intacto. Útil para tests o para el wiring cuando
    `presidio_enabled=False` y no se quiere ni siquiera regex."""

    async def anonymize(self, text: str) -> PiiFilterResult:
        return PiiFilterResult(text=text, replacements=0)

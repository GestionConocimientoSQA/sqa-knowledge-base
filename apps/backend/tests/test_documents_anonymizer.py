"""Tests del anonimizador regex (Fase 4.4)."""

from __future__ import annotations

import pytest

from sqa_kb.documents.anonymizer import (
    DEFAULT_RULES,
    NoopAnonymizer,
    PiiRule,
    RegexAnonymizer,
    _rule,
)
from sqa_kb.ports.gateways import PiiFilter, PiiFilterResult

# ===========================================================================
# anonymize — patrones default
# ===========================================================================


async def test_anonymize_email() -> None:
    r = await RegexAnonymizer().anonymize("Escribí a ana.gomez@cliente.co por favor")
    assert "[EMAIL]" in r.text
    assert "ana.gomez@cliente.co" not in r.text
    assert r.replacements == 1


async def test_anonymize_ipv4() -> None:
    r = await RegexAnonymizer().anonymize("El server está en 10.20.30.40 puerto 5432")
    assert "[IP]" in r.text
    assert "10.20.30.40" not in r.text


async def test_anonymize_credit_card() -> None:
    r = await RegexAnonymizer().anonymize("Pago con 4111-1111-1111-1111 hoy")
    assert "[TARJETA]" in r.text
    assert "4111" not in r.text


async def test_anonymize_phone() -> None:
    r = await RegexAnonymizer().anonymize("Llamar al +57 301 234 5678")
    assert "[TELEFONO]" in r.text


async def test_anonymize_national_id() -> None:
    r = await RegexAnonymizer().anonymize("NIT del cliente: 900.123.456-7")
    assert "[ID]" in r.text
    assert "900.123.456" not in r.text


async def test_anonymize_url_with_credentials() -> None:
    r = await RegexAnonymizer().anonymize(
        "Conexión: postgresql://admin:s3cr3t@db.cliente.com/prod"
    )
    assert "[URL_CON_CREDENCIALES]" in r.text
    assert "s3cr3t" not in r.text


async def test_anonymize_multiple_in_one_text() -> None:
    text = "Mail ana@x.com, IP 8.8.8.8, tel +1 202 555 0143"
    r = await RegexAnonymizer().anonymize(text)
    assert "[EMAIL]" in r.text
    assert "[IP]" in r.text
    assert "[TELEFONO]" in r.text
    assert r.replacements >= 3


# ===========================================================================
# anonymize — no falsos positivos en contenido técnico legítimo
# ===========================================================================


async def test_anonymize_preserves_normal_text() -> None:
    text = "El flujo de CI corre en 3 etapas con 2 reintentos."
    r = await RegexAnonymizer().anonymize(text)
    assert r.text == text
    assert r.replacements == 0


async def test_anonymize_preserves_short_numbers() -> None:
    """Números cortos (años, versiones, conteos) no deben matchear teléfono/ID."""
    text = "Versión 2.0 del año 2026 con 42 tests."
    r = await RegexAnonymizer().anonymize(text)
    assert r.text == text
    assert r.replacements == 0


# ===========================================================================
# Cortocircuitos
# ===========================================================================


async def test_anonymize_empty_text() -> None:
    r = await RegexAnonymizer().anonymize("")
    assert r.text == ""
    assert r.replacements == 0


async def test_anonymize_disabled_is_noop() -> None:
    a = RegexAnonymizer(enabled=False)
    text = "Mail ana@x.com queda intacto"
    r = await a.anonymize(text)
    assert r.text == text
    assert r.replacements == 0


# ===========================================================================
# Reglas custom inyectables
# ===========================================================================


async def test_anonymize_custom_rules() -> None:
    rules = [_rule("proyecto", r"PROY-\d+", "[PROYECTO]")]
    a = RegexAnonymizer(rules=rules)
    r = await a.anonymize("El ticket PROY-1234 está cerrado")
    assert "[PROYECTO]" in r.text
    # Las reglas default NO se aplican (solo las custom).
    r2 = await a.anonymize("mail ana@x.com")
    assert "[EMAIL]" not in r2.text


# ===========================================================================
# detect (auditoría sin reemplazar)
# ===========================================================================


def test_detect_counts_without_replacing() -> None:
    a = RegexAnonymizer()
    counts = a.detect("mail a@b.com y otro c@d.org, IP 1.2.3.4")
    assert counts.get("email") == 2
    assert counts.get("ipv4") == 1


def test_detect_empty_when_clean() -> None:
    a = RegexAnonymizer()
    assert a.detect("texto técnico limpio sin PII") == {}


# ===========================================================================
# NoopAnonymizer
# ===========================================================================


async def test_noop_anonymizer_returns_intact() -> None:
    r = await NoopAnonymizer().anonymize("mail ana@x.com IP 1.2.3.4")
    assert r.text == "mail ana@x.com IP 1.2.3.4"
    assert r.replacements == 0


# ===========================================================================
# Cumple el puerto PiiFilter
# ===========================================================================


def test_regex_anonymizer_satisfies_port() -> None:
    assert isinstance(RegexAnonymizer(), PiiFilter)


def test_noop_anonymizer_satisfies_port() -> None:
    assert isinstance(NoopAnonymizer(), PiiFilter)


async def test_anonymize_returns_pii_filter_result() -> None:
    r = await RegexAnonymizer().anonymize("texto sin pii")
    assert isinstance(r, PiiFilterResult)
    assert r.text == "texto sin pii"
    assert r.replacements == 0


def test_default_rules_have_unique_names() -> None:
    names = [r.name for r in DEFAULT_RULES]
    assert len(names) == len(set(names))


def test_pii_rule_is_frozen() -> None:
    import re
    from dataclasses import FrozenInstanceError

    rule = PiiRule(name="x", pattern=re.compile("a"), replacement="[X]")
    with pytest.raises(FrozenInstanceError):
        rule.name = "y"  # type: ignore[misc]

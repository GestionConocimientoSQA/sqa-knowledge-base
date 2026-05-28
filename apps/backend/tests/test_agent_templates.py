"""Tests del subsistema de templates Jinja2 del agente.

Cubre:
- Cada template empaquetado renderiza con su contexto válido.
- `StrictUndefined`: variables faltantes lanzan UndefinedError.
- Autoescape OFF: caracteres como `<` no se convierten a `&lt;` (clave
  porque los prompts son texto plano para el LLM).
- `list_available()` refleja los .j2 incluidos en el wheel.
- Caracteres especiales / Unicode pasan intactos.
- Iteración sobre listas vacías no rompe.
"""

from __future__ import annotations

import pytest
from jinja2.exceptions import UndefinedError

from sqa_kb.agent.skills import LoadedSkill
from sqa_kb.agent.templates import list_available, render

# ===========================================================================
# Discovery
# ===========================================================================


def test_list_available_includes_core_templates() -> None:
    available = set(list_available())
    assert "system_prompt.j2" in available
    assert "welcome.j2" in available
    assert "classification_proposal.j2" in available
    assert "duplicate_found.j2" in available


# ===========================================================================
# welcome.j2
# ===========================================================================


def test_welcome_renders_with_user_name() -> None:
    out = render("welcome.j2", user_name="Andrés")
    assert "Hola Andrés" in out
    assert "Aria" in out


def test_welcome_missing_user_name_raises() -> None:
    """StrictUndefined: falla rápido si falta una variable."""
    with pytest.raises(UndefinedError):
        render("welcome.j2")


def test_welcome_handles_unicode_in_name() -> None:
    out = render("welcome.j2", user_name="José Ñandú")
    assert "José Ñandú" in out


# ===========================================================================
# system_prompt.j2
# ===========================================================================


def test_system_prompt_with_no_skills() -> None:
    out = render(
        "system_prompt.j2",
        agent_name="Aria",
        user_name="Andrés",
        user_role="gklead",
        mode="capture",
        skills=[],
    )
    assert "Sos Aria" in out
    assert "Andrés" in out
    assert "gklead" in out
    assert "capture" in out
    # Sin skills, el bloque "Skills activos" NO debe aparecer.
    assert "Skills activos" not in out


def test_system_prompt_with_one_skill() -> None:
    skill = LoadedSkill(
        id="sk-1",
        name="Tono SQA",
        body_markdown="Hablá técnico y directo.",
        version=2,
    )
    out = render(
        "system_prompt.j2",
        agent_name="Aria",
        user_name="A",
        user_role="colaborador",
        mode="capture",
        skills=[skill],
    )
    assert "Skills activos (1)" in out
    assert "Tono SQA" in out
    assert "Hablá técnico y directo." in out


def test_system_prompt_with_multiple_skills_order_preserved() -> None:
    """El template itera la lista en el orden recibido — el loader es el
    responsable de pasar orden determinista."""
    skills = [
        LoadedSkill(id="b", name="Skill B", body_markdown="B body", version=1),
        LoadedSkill(id="a", name="Skill A", body_markdown="A body", version=1),
    ]
    out = render(
        "system_prompt.j2",
        agent_name="Aria",
        user_name="A",
        user_role=None,
        mode="capture",
        skills=skills,
    )
    # El orden de aparición debe matchear el de la lista (B antes que A).
    assert out.index("Skill B") < out.index("Skill A")


def test_system_prompt_user_role_none_renders_default() -> None:
    out = render(
        "system_prompt.j2",
        agent_name="Aria",
        user_name="A",
        user_role=None,
        mode="capture",
        skills=[],
    )
    assert "no especificado" in out


def test_system_prompt_does_not_html_escape_skill_body() -> None:
    """Autoescape OFF: caracteres reservados de HTML deben pasar intactos.
    Si esto rompe, el LLM recibiría `&lt;` en lugar de `<` y degradaría
    los prompts."""
    skill = LoadedSkill(
        id="sk-1",
        name="Reglas",
        body_markdown="Si <input> está vacío & nulo, salir.",
        version=1,
    )
    out = render(
        "system_prompt.j2",
        agent_name="Aria",
        user_name="A",
        user_role=None,
        mode="capture",
        skills=[skill],
    )
    assert "<input>" in out
    assert "&lt;" not in out
    assert "&amp;" not in out


def test_system_prompt_missing_required_field_raises() -> None:
    with pytest.raises(UndefinedError):
        render("system_prompt.j2", user_name="A")  # faltan agent_name, mode, etc.


# ===========================================================================
# classification_proposal.j2
# ===========================================================================


def test_classification_proposal_renders_confidence_as_percent() -> None:
    classification = {
        "category": "TEC",
        "document_type": "MTEC",
        "confidence": 0.873,
        "reasoning": "El topic menciona flakiness, automation y CI.",
    }
    out = render(
        "classification_proposal.j2",
        topic="Detección de tests flaky",
        classification=classification,
    )
    assert "Detección de tests flaky" in out
    assert "TEC" in out
    assert "MTEC" in out
    # 87% (con formateo de Jinja `%.0f%%`)
    assert "87%" in out


def test_classification_proposal_missing_field_in_classification_raises() -> None:
    """Si el classification dict no tiene `reasoning`, falla rápido."""
    with pytest.raises(UndefinedError):
        render(
            "classification_proposal.j2",
            topic="x",
            classification={
                "category": "TEC",
                "document_type": "MTEC",
                "confidence": 0.5,
                # falta reasoning
            },
        )


# ===========================================================================
# duplicate_found.j2
# ===========================================================================


def test_duplicate_found_renders_all_existing_docs() -> None:
    existing = [
        {
            "document_id": "TEC-flaky-2026-04-01",
            "filename": "flaky-tests.md",
            "category": "TEC",
            "document_type": "MTEC",
            "distance": 0.32,
        },
        {
            "document_id": "TEC-other-2026-03-15",
            "filename": "other.md",
            "category": "TEC",
            "document_type": "MTEC",
            "distance": 0.51,
        },
    ]
    out = render("duplicate_found.j2", topic="flaky tests", existing=existing)
    assert "flaky-tests.md" in out
    assert "other.md" in out
    assert "0.32" in out
    assert "0.51" in out


def test_duplicate_found_with_empty_list_renders_no_items() -> None:
    """Edge: el caller llamó esto sin docs (no debería pero validamos)."""
    out = render("duplicate_found.j2", topic="x", existing=[])
    assert "flaky" not in out.lower()
    # El template no debe romper aunque no haya items.
    assert "¿Cómo querés seguir?" in out

"""Tests del SkillsLoader + render_system_prompt.

Cubre:
- Loader devuelve skills enabled en orden determinista (id asc).
- Conversión `Skill` (domain) → `LoadedSkill` preserva campos.
- `cache_signature` cambia cuando una versión cambia.
- `render_system_prompt` integra skills correctamente.
- Empty skills list es válido.
- Loader respeta lo que devuelve el repo (no filtra dos veces).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from sqa_kb.agent.skills import (
    LoadedSkill,
    SkillsLoader,
    loaded_from_entity,
    render_system_prompt,
)
from sqa_kb.domain.entities import Skill

# ===========================================================================
# Fake repo
# ===========================================================================


class _FakeSkillRepo:
    def __init__(self, enabled: list[Skill]) -> None:
        self._enabled = enabled
        self.list_enabled_calls = 0

    async def list_enabled(self) -> Sequence[Skill]:
        self.list_enabled_calls += 1
        return list(self._enabled)

    async def get(self, skill_id: str) -> Skill | None:  # noqa: ARG002 — Protocol
        return None

    async def upsert(self, skill: Skill) -> Skill:  # noqa: ARG002
        raise NotImplementedError


def _skill(
    id: str,
    name: str = "X",
    body: str = "body",
    version: int = 1,
    enabled: bool = True,
) -> Skill:
    now = datetime.now(UTC)
    return Skill(
        id=id,
        name=name,
        description="",
        body_markdown=body,
        enabled=enabled,
        version=version,
        updated_by_oid=None,
        updated_at=now,
    )


# ===========================================================================
# Loader
# ===========================================================================


async def test_load_enabled_returns_skills_sorted_by_id() -> None:
    repo = _FakeSkillRepo(
        enabled=[
            _skill("zulu"),
            _skill("alpha"),
            _skill("mike"),
        ]
    )
    loader = SkillsLoader(repo)  # type: ignore[arg-type]
    skills = await loader.load_enabled()
    assert [s.id for s in skills] == ["alpha", "mike", "zulu"]


async def test_load_enabled_empty_returns_empty_list() -> None:
    loader = SkillsLoader(_FakeSkillRepo(enabled=[]))  # type: ignore[arg-type]
    assert await loader.load_enabled() == []


async def test_load_enabled_preserves_body_and_version() -> None:
    repo = _FakeSkillRepo(
        enabled=[_skill("sk-1", name="Foo", body="markdown body", version=3)]
    )
    loader = SkillsLoader(repo)  # type: ignore[arg-type]
    skills = await loader.load_enabled()
    assert skills[0].name == "Foo"
    assert skills[0].body_markdown == "markdown body"
    assert skills[0].version == 3


async def test_load_enabled_hits_repo_each_time() -> None:
    """No cacheamos in-process en 2.2 — cache es responsabilidad del caller
    (snapshot por sesión). Si esto cambia, ajustar comentario y el test."""
    repo = _FakeSkillRepo(enabled=[_skill("a")])
    loader = SkillsLoader(repo)  # type: ignore[arg-type]
    await loader.load_enabled()
    await loader.load_enabled()
    assert repo.list_enabled_calls == 2


# ===========================================================================
# Cache signature
# ===========================================================================


def test_cache_signature_is_stable_for_same_input() -> None:
    loader = SkillsLoader(_FakeSkillRepo([]))  # type: ignore[arg-type]
    skills = [
        LoadedSkill(id="a", name="A", body_markdown="x", version=1),
        LoadedSkill(id="b", name="B", body_markdown="y", version=1),
    ]
    s1 = loader.cache_signature(skills)
    s2 = loader.cache_signature(skills)
    assert s1 == s2
    assert s1 == "a|v1;b|v1"


def test_cache_signature_changes_when_version_bumps() -> None:
    loader = SkillsLoader(_FakeSkillRepo([]))  # type: ignore[arg-type]
    before = [LoadedSkill(id="a", name="A", body_markdown="x", version=1)]
    after = [LoadedSkill(id="a", name="A", body_markdown="x", version=2)]
    assert loader.cache_signature(before) != loader.cache_signature(after)


def test_cache_signature_empty_list_is_empty_string() -> None:
    loader = SkillsLoader(_FakeSkillRepo([]))  # type: ignore[arg-type]
    assert loader.cache_signature([]) == ""


# ===========================================================================
# loaded_from_entity helper
# ===========================================================================


def test_loaded_from_entity_preserves_all_fields() -> None:
    s = _skill("x", name="Skill X", body="content", version=5)
    loaded = loaded_from_entity(s)
    assert loaded.id == "x"
    assert loaded.name == "Skill X"
    assert loaded.body_markdown == "content"
    assert loaded.version == 5
    assert loaded.cache_key == "x|v5"


# ===========================================================================
# render_system_prompt
# ===========================================================================


def test_render_system_prompt_with_empty_skills() -> None:
    out = render_system_prompt(
        user_name="Andrés",
        user_role="gklead",
        mode="capture",
        skills=[],
    )
    assert "Andrés" in out
    assert "gklead" in out
    assert "capture" in out


def test_render_system_prompt_injects_skill_bodies() -> None:
    skills = [
        LoadedSkill(id="s1", name="Tono", body_markdown="técnico y directo", version=1),
    ]
    out = render_system_prompt(
        user_name="A",
        user_role="colaborador",
        mode="capture",
        skills=skills,
    )
    assert "Tono" in out
    assert "técnico y directo" in out


def test_render_system_prompt_default_agent_name_is_aria() -> None:
    out = render_system_prompt(
        user_name="A", user_role=None, mode="capture", skills=[]
    )
    assert "Aria" in out


def test_render_system_prompt_custom_agent_name() -> None:
    out = render_system_prompt(
        user_name="A",
        user_role=None,
        mode="capture",
        skills=[],
        agent_name="Bot42",
    )
    assert "Bot42" in out


@pytest.mark.parametrize("mode", ["capture", "consultation", "ingestion"])
def test_render_system_prompt_supports_all_modes(mode: str) -> None:
    out = render_system_prompt(
        user_name="A", user_role=None, mode=mode, skills=[]
    )
    assert mode in out

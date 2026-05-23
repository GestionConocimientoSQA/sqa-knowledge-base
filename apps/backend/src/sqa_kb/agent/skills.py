"""Skills loader del agente.

Un *skill* es un prompt o regla editable sin redeploy. Vive en la tabla
`skills` (Fase 1B.2). El loader los lee, filtra los `enabled=True` y los
inyecta en el system prompt vía el template `system_prompt.j2`.

Convenciones:
- Orden determinista por `id` ascendente — así Anthropic prompt caching
  hashea el mismo bloque entre turnos.
- Snapshot por sesión: el loader se llama una vez al inicio (cuando
  `awaiting_confirmation` aún es None) y el resultado se guarda en
  `state.active_skills`. NO se re-consulta la DB en cada turno.
- Si un skill se desactiva mid-sesión, la sesión activa lo sigue usando
  hasta que el usuario reinicie — evita comportamiento errático.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqa_kb.agent.templates import render
from sqa_kb.domain.entities import Skill
from sqa_kb.ports.repositories import SkillRepository


@dataclass(frozen=True, slots=True)
class LoadedSkill:
    """Vista plana de un Skill para el template + cache key.

    `cache_key` permite a Anthropic prompt caching detectar cambios sin
    re-hashear todo el body: si el `id|version` cambia, el cache se invalida.
    """

    id: str
    name: str
    body_markdown: str
    version: int

    @property
    def cache_key(self) -> str:
        return f"{self.id}|v{self.version}"


class SkillsLoader:
    """Adapta `SkillRepository` a la forma que consume el template.

    Mantenemos un wrapper en lugar de pasar el repo directo porque:
    - El loader podría agregar caching in-process en el futuro.
    - Los nodos del grafo no deberían acoplarse al puerto `SkillRepository`.
    - Tests pueden mockear `SkillsLoader` sin tocar repos.
    """

    def __init__(self, repo: SkillRepository) -> None:
        self._repo = repo

    async def load_enabled(self) -> list[LoadedSkill]:
        """Devuelve los skills activos en orden determinista (por id asc).

        Cada call golpea la DB — el caller cachea el resultado por sesión
        (ver convenciones del módulo)."""
        raw = await self._repo.list_enabled()
        skills = [
            LoadedSkill(
                id=s.id,
                name=s.name,
                body_markdown=s.body_markdown,
                version=s.version,
            )
            for s in raw
        ]
        skills.sort(key=lambda s: s.id)
        return skills

    def cache_signature(self, skills: list[LoadedSkill]) -> str:
        """Concatena `cache_key` de todos los skills para detectar cambios.

        Si dos snapshots devuelven la misma signature, el system prompt
        renderizado es idéntico → Anthropic cache hit garantizado.
        """
        return ";".join(s.cache_key for s in skills)


def render_system_prompt(
    *,
    user_name: str,
    user_role: str | None,
    mode: str,
    skills: list[LoadedSkill],
    agent_name: str = "Aria",
) -> str:
    """Renderiza el system prompt completo con skills inyectados.

    Función libre (no método) porque no tiene estado — facilita testear
    sin instanciar `SkillsLoader`. Los nodos del grafo la llaman con el
    snapshot ya cargado de `state.active_skills`.
    """
    return render(
        "system_prompt.j2",
        agent_name=agent_name,
        user_name=user_name,
        user_role=user_role,
        mode=mode,
        skills=skills,
    )


def loaded_from_entity(skill: Skill) -> LoadedSkill:
    """Helper para convertir un `Skill` (domain) → `LoadedSkill`. Usado en
    tests; el loader real lo hace inline."""
    return LoadedSkill(
        id=skill.id,
        name=skill.name,
        body_markdown=skill.body_markdown,
        version=skill.version,
    )

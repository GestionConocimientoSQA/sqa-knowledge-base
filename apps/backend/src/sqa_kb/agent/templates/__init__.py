"""Templates Jinja2 de prompts del agente.

Decisiones de diseño:
- **`StrictUndefined`**: si un template referencia una variable que no se
  pasó, falla con `UndefinedError` en lugar de renderizar string vacío.
  Atrapamos bugs de los nodos del grafo en tests, no en producción.
- **Sin autoescape**: los prompts son texto plano para el LLM, no HTML.
  Activarlo escaparía `<`, `&`, etc. y degradaría el prompt.
- **`PackageLoader`**: los `.j2` se empaquetan con el wheel, no se leen
  del filesystem en runtime. Funciona igual en local que en el container
  de Azure.

Uso típico desde un nodo del grafo:

    from sqa_kb.agent.templates import render
    msg = render("welcome.j2", user_name=state.user_name)
"""

from __future__ import annotations

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

# Environment singleton — Jinja2 cachea templates parseados internamente.
_env = Environment(
    loader=PackageLoader("sqa_kb.agent", "templates"),
    undefined=StrictUndefined,
    autoescape=select_autoescape(disabled_extensions=("j2",), default=False),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=False,
)


def render(template_name: str, /, **context: object) -> str:
    """Renderiza un template `.j2` con las variables que se le pasen.

    Lanza `jinja2.exceptions.UndefinedError` si el template referencia una
    variable que no está en `context`. Eso es intencional — atrapa bugs
    en tests antes de que lleguen al LLM con un prompt parcial.
    """
    template = _env.get_template(template_name)
    return template.render(**context)


def list_available() -> list[str]:
    """Devuelve los nombres de templates disponibles. Útil para tests
    que verifican que el set completo está empaquetado."""
    return sorted(_env.list_templates(extensions=["j2"]))

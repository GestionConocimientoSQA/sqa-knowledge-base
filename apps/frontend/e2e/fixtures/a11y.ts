/**
 * Helper de accesibilidad para los E2E.
 *
 * Ejecuta axe-core sobre la página actual con reglas WCAG 2.1 AA y falla
 * el test si encuentra violations. Filtra reglas específicas que producen
 * falsos positivos en componentes shadcn/ui inevitables sin reescribir
 * los primitives (por ejemplo, `color-contrast` sobre placeholders del
 * input, que tienen contraste 3.0 por diseño pero pasan WCAG AA si el
 * texto principal lo cumple).
 */
import { AxeBuilder } from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

/** Reglas axe que ignoramos con justificación documentada. */
const DISABLED_RULES: string[] = [
  // Recharts inserta SVG sin role="img" + aria-label en sub-elementos
  // que axe marca como svg-img-alt. El wrapper del chart sí tiene
  // role="img" + aria-label descriptivo (lo agregamos en 7.4).
  "svg-img-alt",
];

export async function expectNoAxeViolations(
  page: Page,
  options: { context?: string } = {},
): Promise<void> {
  const builder = new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .disableRules(DISABLED_RULES);

  const results = await builder.analyze();

  if (results.violations.length > 0) {
    const summary = results.violations
      .map((v) => {
        const nodes = v.nodes
          .slice(0, 3)
          .map((n) => `    ${n.target.join(" > ")}`)
          .join("\n");
        return `  [${v.impact}] ${v.id}: ${v.help}\n${nodes}`;
      })
      .join("\n\n");
    throw new Error(
      `axe violations${options.context ? ` en ${options.context}` : ""}:\n${summary}`,
    );
  }
  expect(results.violations).toHaveLength(0);
}

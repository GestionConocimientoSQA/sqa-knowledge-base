import { test } from "./fixtures/auth";
import { expectNoAxeViolations } from "./fixtures/a11y";

/**
 * Auditoría axe-core de las páginas críticas (WCAG 2.1 AA).
 *
 * Estrategia: una run por ruta clave, esperando al estado "populated"
 * antes de auditar (no auditamos skeletons — son intencionalmente sin
 * texto). Los specs funcionales viven en `*.spec.ts`; este archivo
 * concentra los checks de a11y para que sea fácil seguirles el pulso.
 */

test.describe("Accesibilidad (axe-core WCAG 2.1 AA)", () => {
  test("/login", async ({ page }) => {
    await page.goto("/login");
    await expectNoAxeViolations(page, { context: "/login" });
  });

  test("/dashboard (GK Lead — global)", async ({ page, loginAs }) => {
    await loginAs("gklead");
    await page.goto("/dashboard");
    // Esperar a que los KPIs y al menos un chart hayan renderizado.
    await page.getByText(/Capturas · 30 días/i).waitFor();
    await page.getByText(/distribución por carpeta/i).waitFor();
    await expectNoAxeViolations(page, { context: "/dashboard (admin)" });
  });

  test("/dashboard (Capturador — resumen personal)", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/dashboard");
    await page.getByRole("heading", { name: /resumen personal/i }).waitFor();
    await expectNoAxeViolations(page, { context: "/dashboard (capturador)" });
  });

  test("/explorer (lista completa)", async ({ page, loginAs }) => {
    await loginAs("capturador");
    await page.goto("/explorer");
    await page.getByText(/45 resultados/i).waitFor();
    await expectNoAxeViolations(page, { context: "/explorer" });
  });

  test("/explorer con filtros activos", async ({ page, loginAs }) => {
    await loginAs("capturador");
    await page.goto("/explorer?carpetas=TEC&tipos=MTEC");
    await page.getByText(/5 resultados/i).waitFor();
    await expectNoAxeViolations(page, { context: "/explorer (con filtros)" });
  });

  test("/explorer/[docId] (detalle)", async ({ page, loginAs }) => {
    await loginAs("gklead");
    await page.goto("/explorer/TEC-flakiness-detection-2026-04-22");
    await page
      .getByRole("heading", { name: /Detección y aislamiento/i })
      .waitFor();
    await expectNoAxeViolations(page, { context: "/explorer/[docId]" });
  });

  test("/chat (selector de modos)", async ({ page, loginAs }) => {
    await loginAs("capturador");
    await page.goto("/chat");
    await page
      .getByRole("heading", { name: /¿Cómo querés trabajar con Aria/i })
      .waitFor();
    await expectNoAxeViolations(page, { context: "/chat" });
  });

  test("/my-captures (empty state)", async ({ page, loginAs }) => {
    await loginAs("capturador");
    await page.goto("/my-captures");
    await page.getByText(/aún no capturaste nada/i).waitFor();
    await expectNoAxeViolations(page, { context: "/my-captures" });
  });
});

/**
 * Smoke E2E de la cola de ingesta (Fase 8.5).
 *
 * Cubre el camino feliz end-to-end con el stub frontend:
 *   1. Gating: capturador no puede ver la cola.
 *   2. Owner ve la página con tabs + queue + UploadZone.
 *   3. Owner clasifica un item pendiente → el item aparece en "En revisión".
 *   4. Owner abre el detail → ve el TraceabilityForm.
 *
 * No probamos la aprobación real porque dispararía la mutación contra el
 * stub y luego redirige; el detalle del form ya está cubierto por unit
 * tests. El smoke valida el wiring de las pantallas y la navegación.
 */
import { test, expect } from "./fixtures/auth";

test.describe("Cola de ingesta", () => {
  test("capturador ve mensaje de acceso restringido en /ingestion", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/ingestion");

    await expect(page.getByText(/acceso restringido/i)).toBeVisible();
    await expect(page.getByLabel(/filtros por estado/i)).not.toBeVisible();
  });

  test("owner ve UploadZone + tabs + queue con seed", async ({
    page,
    loginAs,
  }) => {
    await loginAs("owner");
    await page.goto("/ingestion");

    await expect(
      page.getByRole("heading", { level: 2, name: /cola de ingesta/i }),
    ).toBeVisible();
    await expect(page.getByTestId("upload-zone")).toBeVisible();

    // Las 4 tabs canónicas
    const tablist = page.getByLabel(/filtros por estado/i);
    await expect(tablist.getByRole("tab", { name: /pendientes/i })).toBeVisible();
    await expect(tablist.getByRole("tab", { name: /en revisión/i })).toBeVisible();
    await expect(tablist.getByRole("tab", { name: /completados/i })).toBeVisible();
    await expect(tablist.getByRole("tab", { name: /rechazados/i })).toBeVisible();

    // El seed tiene 1 item pendiente-metadata
    await expect(
      page.getByText(/Politica_Seguridad_QA_v3\.docx/),
    ).toBeVisible();
  });

  test("clasificar un item pendiente lo mueve a 'En revisión'", async ({
    page,
    loginAs,
  }) => {
    await loginAs("owner");
    await page.goto("/ingestion");

    const row = page.getByTestId("ingestion-row-ing-0001");
    await expect(row).toBeVisible();

    await row.getByRole("button", { name: /clasificar/i }).click();

    // Cambiamos a la tab "En revisión" y verificamos que aparece ahí.
    await page.getByRole("tab", { name: /en revisión/i }).click();
    await expect(
      page.getByText(/Politica_Seguridad_QA_v3\.docx/),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("detail page muestra el TraceabilityForm para un item en revisión", async ({
    page,
    loginAs,
  }) => {
    await loginAs("gklead");
    // ing-0002 está en seed como en-revision
    await page.goto("/ingestion/ing-0002");

    await expect(
      page.getByRole("heading", { name: /Plantilla-Casos-Aceptacion\.xlsx/ }),
    ).toBeVisible();
    await expect(page.getByRole("form", { name: /trazabilidad/i })).toBeVisible();
    await expect(page.getByLabel(/aprobado por/i)).toHaveValue(
      "Andrés Altamiranda",
    );
    await expect(page.getByLabel(/carpeta temática/i)).toHaveValue("PROC");
    await expect(page.getByLabel(/tipo de documento/i)).toHaveValue("FORM");
  });
});

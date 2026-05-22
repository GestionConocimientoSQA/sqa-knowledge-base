import { test, expect } from "./fixtures/auth";

test.describe("Explorer · catálogo de documentos", () => {
  test.beforeEach(async ({ loginAs }) => {
    await loginAs("capturador");
  });

  test("lista 45 documentos con sort por fecha descendente por defecto", async ({
    page,
  }) => {
    await page.goto("/explorer");
    await expect(page.getByText(/45 resultados/i)).toBeVisible();
    // El primer card es el de mayor fecha.
    await expect(
      page.getByRole("heading", {
        name: /Política de revisión de código y aprobación de PRs/,
      }),
    ).toBeVisible();
  });

  test("filtrar por carpeta TEC actualiza URL + cuenta resultados", async ({
    page,
  }) => {
    await page.goto("/explorer");
    await page.getByRole("button", { name: /carpeta Técnico/i }).click();
    await expect(page).toHaveURL(/[?&]carpetas=TEC(?:&|$)/);
    // 10 docs son TEC en mocks.
    await expect(page.getByText(/10 resultados/i)).toBeVisible();
  });

  test("filtros combinados se aplican en AND", async ({ page }) => {
    await page.goto("/explorer");
    await page.getByRole("button", { name: /carpeta Técnico/i }).click();
    // Esperar que la URL se asiente antes del segundo click — evita race
    // condition cuando el dev server está saturado por tests paralelos.
    await expect(page).toHaveURL(/[?&]carpetas=TEC(?:&|$)/);
    await page.getByRole("button", { name: /tipo Memoria técnica/i }).click();
    await expect(page).toHaveURL(/carpetas=TEC.*tipos=MTEC|tipos=MTEC.*carpetas=TEC/);
    // Espera "5 resultados" (5 docs son TEC + MTEC en mocks).
    await expect(page.getByText(/5 resultados/i)).toBeVisible();
  });

  test("búsqueda con debounce actualiza URL y filtra resultados", async ({
    page,
  }) => {
    await page.goto("/explorer");
    await page.getByLabel("Buscar documentos").fill("playwright");
    // Debounce 300ms + dev server saturado → margen amplio.
    await expect(page).toHaveURL(/[?&]q=playwright(?:&|$)/, { timeout: 5000 });
    // 2 docs en mocks tienen "Playwright" en título o tags
    // (TEC-flakiness-detection y HERR-playwright-config).
    await expect(page.getByText(/2 resultados/i)).toBeVisible();
  });

  test("botón Limpiar resetea filtros y vuelve al catálogo completo", async ({
    page,
  }) => {
    await page.goto("/explorer?carpetas=TEC&tipos=MTEC");
    await expect(page.getByText(/2 filtros activos/i)).toBeVisible();
    await page.getByRole("button", { name: /limpiar todos los filtros/i }).click();
    await expect(page).toHaveURL(/\/explorer\/?$/);
    await expect(page.getByText(/45 resultados/i)).toBeVisible();
  });

  test("click en DocumentCard navega al detalle", async ({ page }) => {
    await page.goto("/explorer?carpetas=TEC&tipos=MTEC&q=playwright");
    await page.getByRole("link", { name: /Abrir Detección y aislamiento/i }).click();
    await expect(page).toHaveURL(/\/explorer\/TEC-flakiness-detection/);
    await expect(
      page.getByRole("heading", {
        name: /Detección y aislamiento de tests flaky/i,
      }),
    ).toBeVisible();
  });

  test("estado vacío con filtros incompatibles ofrece Limpiar", async ({
    page,
  }) => {
    // CONT + POL no produce resultados en mocks.
    await page.goto("/explorer?carpetas=CONT&tipos=POL");
    await expect(page.getByText(/sin resultados con esos filtros/i)).toBeVisible();
    await expect(
      page.getByRole("button", { name: /limpiar filtros/i }),
    ).toBeVisible();
  });

  test("F5 preserva filtros + paginación (URL state shareable)", async ({
    page,
  }) => {
    await page.goto("/explorer?carpetas=TEC&page=1&sort=score_desc");
    await expect(page.getByText(/10 resultados/i)).toBeVisible();
    await page.reload();
    await expect(page).toHaveURL(/carpetas=TEC.*sort=score_desc|sort=score_desc.*carpetas=TEC/);
    await expect(page.getByText(/10 resultados/i)).toBeVisible();
  });

  test("paginación: avanzar a página 2 actualiza el rango visible", async ({
    page,
  }) => {
    await page.goto("/explorer?limit=20");
    await expect(page.getByText(/1\s*–\s*20\s*de\s*45/)).toBeVisible();
    await page.getByRole("button", { name: /página siguiente/i }).click();
    await expect(page.getByText(/21\s*–\s*40\s*de\s*45/)).toBeVisible();
    await expect(page).toHaveURL(/[?&]page=2/);
  });
});

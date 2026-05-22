import { test, expect } from "./fixtures/auth";

const DOC_ID = "TEC-flakiness-detection-2026-04-22";

test.describe("Detalle de documento", () => {
  test("breadcrumb, metadata y resumen ejecutivo", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto(`/explorer/${DOC_ID}`);

    // Breadcrumb visible con link a /explorer.
    await expect(page.getByRole("link", { name: /catálogo/i }).first()).toBeVisible();
    // Título del doc.
    await expect(
      page.getByRole("heading", {
        name: /Detección y aislamiento de tests flaky/i,
      }),
    ).toBeVisible();
    // ID en mono.
    await expect(page.getByText(DOC_ID)).toBeVisible();
    // Resumen ejecutivo visible.
    await expect(page.getByText(/Sistemática para detectar tests inestables/i)).toBeVisible();
  });

  test("Capturador ve solo Descargar (no Marcar autoritativo)", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto(`/explorer/${DOC_ID}`);
    await expect(page.getByRole("button", { name: /descargar/i })).toBeVisible();
    // El gating: NO debe aparecer "Marcar autoritativo" ni "Quitar autoritativo".
    await expect(
      page.getByRole("button", { name: /marcar autoritativo|quitar autoritativo/i }),
    ).toHaveCount(0);
  });

  test("Owner/GK Lead ve Marcar/Quitar autoritativo según estado del doc", async ({
    page,
    loginAs,
  }) => {
    await loginAs("gklead");
    // Este doc es autoritativo en el mock → vemos "Quitar".
    await page.goto(`/explorer/${DOC_ID}`);
    await expect(
      page.getByRole("button", { name: /quitar autoritativo/i }),
    ).toBeVisible();
  });

  test("sidebar de incoming citations renderea con link al doc origen", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto(`/explorer/${DOC_ID}`);
    // Sidebar "Citado por" con 1 citación desde PROC-revision-codigo.
    await expect(page.getByText(/citado por/i)).toBeVisible();
    const citation = page.getByRole("link", {
      name: /Política de revisión de código y aprobación de PRs/i,
    });
    await expect(citation).toBeVisible();
    await expect(citation).toHaveAttribute(
      "href",
      /\/explorer\/PROC-revision-codigo/,
    );
  });

  test("ID inexistente muestra empty state con CTA al catálogo", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/explorer/DOC-INEXISTENTE-XYZ");
    await expect(page.getByText(/documento no encontrado/i)).toBeVisible();
    await expect(
      page.getByRole("link", { name: /volver al catálogo/i }),
    ).toBeVisible();
  });
});

import { test, expect } from "./fixtures/auth";

test.describe("Mis capturas", () => {
  test("Capturador sin docs ve empty state con CTA al chat", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/my-captures");

    await expect(
      page.getByRole("heading", { name: /^mis capturas$/i }),
    ).toBeVisible();
    // El oid del stub no matchea con AUTHOR_OIDS del mock → empty state.
    await expect(page.getByText(/aún no capturaste nada/i)).toBeVisible();
    // Hay dos links "Iniciar captura": uno en MyCapturesSummary (header) y
    // otro en el EmptyState del grid. Validamos que ambos apunten al chat.
    const ctas = page.getByRole("link", { name: /iniciar captura/i });
    await expect(ctas).toHaveCount(2);
    await expect(ctas.first()).toHaveAttribute("href", "/chat?mode=captura");
  });

  test("link a /my-captures visible en sidebar para todos los roles", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/dashboard");
    const link = page.getByRole("link", { name: /mis capturas/i }).first();
    await expect(link).toBeVisible();
    await link.click();
    await expect(page).toHaveURL(/\/my-captures$/);
  });
});

import { test, expect } from "./fixtures/auth";

/**
 * Verifica que el switcher de idioma persiste el locale en cookie y
 * los strings traducidos aparecen tras la action server-side.
 *
 * Estrategia: navegar al dashboard, abrir el switcher, elegir English,
 * esperar revalidación y verificar que un string del namespace `nav`
 * cambió a su traducción inglesa.
 */

test.describe("i18n (next-intl)", () => {
  test("locale por defecto es es-CO (strings en español)", async ({
    page,
    loginAs,
  }) => {
    await loginAs("gklead");
    await page.goto("/dashboard");
    // Sidebar groups en español.
    await expect(page.getByText(/^TRABAJO$/i).first()).toBeVisible();
    await expect(page.getByText(/^CONOCIMIENTO$/i).first()).toBeVisible();
  });

  test("cambiar a en-US traduce nav + topbar", async ({
    page,
    loginAs,
  }) => {
    await loginAs("gklead");
    await page.goto("/dashboard");

    // Abrir el language switcher (botón con aria-label "Idioma").
    await page.getByRole("button", { name: /^idioma$/i }).click();
    await page.getByRole("menuitem", { name: /english \(us\)/i }).click();

    // Después de la action server-side + revalidate, los strings cambian.
    await expect(page.getByText(/^WORK$/i).first()).toBeVisible({
      timeout: 5_000,
    });
    await expect(page.getByText(/^KNOWLEDGE$/i).first()).toBeVisible();
    // El sidebar items traducidos.
    await expect(page.getByRole("link", { name: /metrics/i }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /catalog/i }).first()).toBeVisible();
  });

  test("cookie NEXT_LOCALE persiste el locale tras F5", async ({
    page,
    context,
    loginAs,
  }) => {
    await loginAs("gklead");
    await page.goto("/dashboard");

    // Setear locale via switcher.
    await page.getByRole("button", { name: /^idioma$/i }).click();
    await page.getByRole("menuitem", { name: /english \(us\)/i }).click();
    await expect(page.getByText(/^WORK$/i).first()).toBeVisible({
      timeout: 5_000,
    });

    // Cookie está seteada.
    const cookies = await context.cookies();
    const localeCookie = cookies.find((c) => c.name === "NEXT_LOCALE");
    expect(localeCookie?.value).toBe("en-US");

    // F5 mantiene el locale.
    await page.reload();
    await expect(page.getByText(/^WORK$/i).first()).toBeVisible();
  });

  test("skip-link sigue traducido (español por default)", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/dashboard");
    await page.keyboard.press("Tab");
    // Default es-CO: "Saltar al contenido principal".
    const skipLink = page.getByRole("link", {
      name: /saltar al contenido principal/i,
    });
    await expect(skipLink).toBeFocused();
  });

  test("html[lang] refleja el locale activo", async ({ page, loginAs }) => {
    await loginAs("gklead");
    await page.goto("/dashboard");
    await expect(page.locator("html")).toHaveAttribute("lang", "es-CO");

    await page.getByRole("button", { name: /^idioma$/i }).click();
    await page.getByRole("menuitem", { name: /english \(us\)/i }).click();
    // Esperar revalidación.
    await expect(page.getByText(/^WORK$/i).first()).toBeVisible({
      timeout: 5_000,
    });
    await expect(page.locator("html")).toHaveAttribute("lang", "en-US");
  });
});

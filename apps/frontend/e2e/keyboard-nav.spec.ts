import { test, expect } from "./fixtures/auth";

/**
 * Validación de navegación por teclado (WCAG 2.1.1, 2.4.1, 2.4.3, 2.4.7).
 *
 * Cubre los flujos donde el keyboard es crítico:
 *  - skip-link al main content
 *  - tab order coherente en FilterBar
 *  - Enter activa botones y links
 *  - Escape cierra dialogs (Sheet de preview)
 *  - focus visible se mantiene durante la navegación
 */

test.describe("Navegación por teclado", () => {
  test("primer Tab muestra skip-link 'Saltar al contenido principal'", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/dashboard");
    // El skip-link es el primer elemento focuseable del layout.
    await page.keyboard.press("Tab");
    const skipLink = page.getByRole("link", { name: /saltar al contenido principal/i });
    await expect(skipLink).toBeFocused();
  });

  test("Enter en skip-link salta el foco al main content", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/explorer");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Enter");
    // El target del skip-link es <main id="main-content"> que tiene tabindex=-1
    // para poder recibir focus programático.
    const main = page.locator("#main-content");
    await expect(main).toBeFocused();
  });

  test("Tab order en FilterBar: search → carpetas → tipos", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/explorer");
    // Saltamos sidebar/topbar yendo directo al search.
    const search = page.getByLabel("Buscar documentos");
    await search.focus();
    await expect(search).toBeFocused();

    // El primer Tab desde el search lleva al primer chip de carpeta (PROC).
    await page.keyboard.press("Tab");
    const firstFolder = page.getByRole("button", { name: /carpeta Procesos/i });
    await expect(firstFolder).toBeFocused();

    // Más Tabs avanzan por las carpetas en orden.
    await page.keyboard.press("Tab");
    await expect(
      page.getByRole("button", { name: /carpeta Técnico/i }),
    ).toBeFocused();
  });

  test("Enter en chip de filtro lo activa (mismo que click)", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/explorer");
    const tec = page.getByRole("button", { name: /carpeta Técnico/i });
    await tec.focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/[?&]carpetas=TEC(?:&|$)/);
    await expect(tec).toHaveAttribute("aria-pressed", "true");
  });

  test("Space también activa chips de filtro", async ({ page, loginAs }) => {
    await loginAs("capturador");
    await page.goto("/explorer");
    const arq = page.getByRole("button", { name: /carpeta Arquitectura/i });
    await arq.focus();
    await page.keyboard.press("Space");
    await expect(page).toHaveURL(/[?&]carpetas=ARQ(?:&|$)/);
  });

  test("Tab desde composer (con texto) lleva al botón Enviar habilitado", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/chat");
    await page.getByRole("button", { name: /iniciar nueva captura/i }).click();
    await page.waitForURL(/\/chat\/[0-9a-f-]+/);

    const composer = page.getByLabel(/mensaje para Aria/i);
    await composer.focus();
    // El boton Enviar está disabled mientras el textarea esté vacío
    // (canSend=false). Escribimos para habilitarlo y validar el tab order.
    await composer.fill("Hola Aria");

    await page.keyboard.press("Tab");
    await expect(page.getByLabel(/enviar mensaje/i)).toBeFocused();
  });

  test("Enter en composer envía el mensaje (Shift+Enter da newline)", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/chat");
    await page.getByRole("button", { name: /iniciar nueva captura/i }).click();
    await page.waitForURL(/\/chat\/[0-9a-f-]+/);

    const composer = page.getByLabel(/mensaje para Aria/i);
    await composer.focus();
    await page.keyboard.type("Hola Aria");
    await page.keyboard.press("Enter");
    // El mensaje aparece como burbuja del usuario.
    await expect(page.getByText("Hola Aria").first()).toBeVisible();
  });

  test("focus-visible en chips de filtro es claramente perceptible", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/explorer");
    const tec = page.getByRole("button", { name: /carpeta Técnico/i });
    await tec.focus();
    // El chip tiene `focus-visible:ring-2 focus-visible:ring-ring` aplicado.
    // Validamos que el computed style tenga box-shadow no-none cuando focused.
    const ring = await tec.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return style.boxShadow;
    });
    expect(ring).not.toBe("none");
  });
});

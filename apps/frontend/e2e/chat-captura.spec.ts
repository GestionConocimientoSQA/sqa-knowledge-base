import { test, expect } from "./fixtures/auth";

test.describe("Chat captura · modo A end-to-end", () => {
  test("crear sesión y completar flujo de captura con streaming", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/chat");

    // Selector de modos visible.
    await expect(
      page.getByRole("heading", { name: /¿Cómo querés trabajar con Aria hoy\?/i }),
    ).toBeVisible();

    // Iniciar nueva captura → navega a /chat/[sessionId].
    await page.getByRole("button", { name: /iniciar nueva captura/i }).click();
    await expect(page).toHaveURL(/\/chat\/[0-9a-f-]+/, { timeout: 10_000 });

    // Header con modo A · captura (texto literal en DOM, uppercase es CSS).
    await expect(page.getByText(/Modo A · Captura/i)).toBeVisible();

    // Stepper 0-5 visible.
    await expect(
      page.getByRole("list", { name: /etapas de la captura/i }),
    ).toBeVisible();
    await expect(page.getByText(/Bienvenida/)).toBeVisible();
    await expect(page.getByText(/Generación/)).toBeVisible();

    // Composer disponible.
    const composer = page.getByLabel(/mensaje para Aria/i);
    await expect(composer).toBeVisible();

    // Enviar mensaje.
    await composer.fill("Quiero documentar la política de revisión de código");
    await page.getByLabel(/enviar mensaje/i).click();

    // El mensaje del usuario aparece.
    await expect(
      page.getByText(/Quiero documentar la política de revisión de código/),
    ).toBeVisible();

    // Eventualmente aparece la classification (TEC/MTEC con confianza 86%).
    await expect(page.getByText(/clasificación sugerida/i)).toBeVisible({
      timeout: 10_000,
    });

    // El streaming termina con scoring y artifact.
    await expect(page.getByText(/scoring de captura/i)).toBeVisible({
      timeout: 15_000,
    });
    await expect(
      page.getByText(/MTEC-captura-mock-2026-05-19\.docx/i),
    ).toBeVisible({ timeout: 15_000 });
  });

  test("Capturador no ve footer de tokenUsage en mensajes del agente", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/chat");
    await page.getByRole("button", { name: /iniciar nueva captura/i }).click();
    await page.waitForURL(/\/chat\/[0-9a-f-]+/);

    await page.getByLabel(/mensaje para Aria/i).fill("Hola Aria");
    await page.getByLabel(/enviar mensaje/i).click();

    // Esperar que el streaming termine (scoring aparece al final).
    await expect(page.getByText(/scoring de captura/i)).toBeVisible({
      timeout: 15_000,
    });

    // El footer tiene formato "X in · Y out · USD Z · model"; no debe verse.
    await expect(page.getByText(/in · .* out · USD/i)).toHaveCount(0);
  });

  test("Owner/GK Lead SÍ ve footer de tokenUsage", async ({
    page,
    loginAs,
  }) => {
    await loginAs("gklead");
    await page.goto("/chat");
    await page.getByRole("button", { name: /iniciar nueva captura/i }).click();
    await page.waitForURL(/\/chat\/[0-9a-f-]+/);

    await page.getByLabel(/mensaje para Aria/i).fill("Hola Aria");
    await page.getByLabel(/enviar mensaje/i).click();

    await expect(page.getByText(/scoring de captura/i)).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText(/in · .* out · USD/i)).toBeVisible({
      timeout: 5_000,
    });
  });

  test("F5 preserva la sesión y los mensajes (persistencia localStorage)", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/chat");
    await page.getByRole("button", { name: /iniciar nueva captura/i }).click();
    await page.waitForURL(/\/chat\/[0-9a-f-]+/);
    const sessionUrl = page.url();

    await page.getByLabel(/mensaje para Aria/i).fill("Mensaje persistido");
    await page.getByLabel(/enviar mensaje/i).click();

    // Esperar que el message-end persista la sesión.
    await expect(page.getByText(/scoring de captura/i)).toBeVisible({
      timeout: 15_000,
    });

    await page.reload();
    await expect(page).toHaveURL(sessionUrl);
    await expect(page.getByText(/Mensaje persistido/)).toBeVisible();
  });
});

test.describe("Chat consulta · modo B", () => {
  test("modo B muestra pill C en lugar del stepper 0-5", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/chat");
    await page.getByRole("button", { name: /iniciar nueva consulta/i }).click();
    await page.waitForURL(/\/chat\/[0-9a-f-]+/);

    // Header con modo B · consulta (texto literal en DOM, uppercase es CSS).
    await expect(page.getByText(/Modo B · Consulta/i)).toBeVisible();
    // Pill C visible.
    await expect(page.getByText(/consultando base de conocimiento/i)).toBeVisible();
    // NO debe estar el stepper de captura.
    await expect(
      page.getByRole("list", { name: /etapas de la captura/i }),
    ).toHaveCount(0);
  });
});

import { test, expect } from "./fixtures/auth";

test.describe("Autenticación (auth stub)", () => {
  test("usuario sin sesión es redirigido a /login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("login como Capturador deja al usuario en /dashboard con sesión activa", async ({
    page,
    loginAs,
  }) => {
    const user = await loginAs("capturador");
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/dashboard$/);
    // El badge del usuario aparece en el sidebar y/o topbar.
    await expect(page.getByText(user.name).first()).toBeVisible();
  });

  test("login como Owner muestra dashboard global (isAdmin=true)", async ({
    page,
    loginAs,
  }) => {
    await loginAs("owner");
    await page.goto("/dashboard");
    // Owner ve KPIs globales (no la variante "Resumen personal" del Capturador).
    await expect(page.getByText(/Capturas · 30 días/i)).toBeVisible();
    await expect(page.getByText(/Consultas · 30 días/i)).toBeVisible();
  });

  test("login como GK Lead muestra dashboard global completo", async ({
    page,
    loginAs,
  }) => {
    await loginAs("gklead");
    await page.goto("/dashboard");
    await expect(page.getByText(/Capturas · 30 días/i)).toBeVisible();
    await expect(page.getByText(/Score promedio/i)).toBeVisible();
  });

  test("Capturador NO ve los KPIs globales (ve resumen personal)", async ({
    page,
    loginAs,
  }) => {
    await loginAs("capturador");
    await page.goto("/dashboard");
    // El header del CapturadorDashboard usa "Resumen personal".
    await expect(page.getByRole("heading", { name: /resumen personal/i })).toBeVisible();
    // Y NO ven los KPIs globales — "Capturas · 30 días" es exclusivo del AdminDashboard.
    await expect(page.getByText(/Capturas · 30 días/i)).toHaveCount(0);
    await expect(page.getByText(/Consultas · 30 días/i)).toHaveCount(0);
    // Tampoco el chart por carpeta del admin.
    await expect(page.getByText(/distribución por carpeta/i)).toHaveCount(0);
  });
});

/**
 * Fixture de autenticación para los E2E.
 *
 * El auth-stub del frontend persiste el usuario en `localStorage` bajo la
 * clave `sqa-kb:auth-user`. Los tests E2E setean esa entrada directamente
 * vía `page.addInitScript()` antes de la primera navegación, evitando pasar
 * por la UI de login en cada test. Esto deja la UI de login probada por
 * separado en `auth.spec.ts`.
 *
 * Cuando Fase 11 reemplaza el stub por MSAL real, este fixture se actualiza
 * para usar `storageState` con un token JWT mock — la interfaz de los tests
 * no cambia.
 */
import { test as base, type Page } from "@playwright/test";

const STORAGE_KEY = "sqa-kb:auth-user";

export type RoleId = "capturador" | "owner" | "gklead";

export interface E2EUser {
  oid: string;
  email: string;
  name: string;
  roleId: RoleId;
  isAdmin: boolean;
}

const USER_BY_ROLE: Record<RoleId, E2EUser> = {
  capturador: {
    oid: "stub-capturador-00000000",
    email: "lucia.vargas@sqa.co",
    name: "Lucía Vargas",
    roleId: "capturador",
    isAdmin: false,
  },
  owner: {
    oid: "stub-owner-00000000",
    email: "camila.pereyra@sqa.co",
    name: "Camila Pereyra",
    roleId: "owner",
    isAdmin: true,
  },
  gklead: {
    oid: "stub-gklead-00000000",
    email: "andres.altamiranda@sqa.co",
    name: "Andrés Altamiranda",
    roleId: "gklead",
    isAdmin: true,
  },
};

/**
 * Inyecta el usuario en localStorage ANTES de cargar la página. Se ejecuta
 * en el contexto del page, por lo que `window.localStorage` está disponible.
 */
export async function seedUser(page: Page, roleId: RoleId): Promise<E2EUser> {
  const user = USER_BY_ROLE[roleId];
  await page.addInitScript(
    ({ key, value }) => {
      window.localStorage.setItem(key, value);
    },
    { key: STORAGE_KEY, value: JSON.stringify(user) },
  );
  return user;
}

/** Limpia cualquier sesión persistida — usar para tests del flujo de login. */
export async function clearAuth(page: Page): Promise<void> {
  await page.addInitScript((key) => {
    window.localStorage.removeItem(key);
  }, STORAGE_KEY);
}

/**
 * Versión extendida de `test` con un fixture `loginAs(role)` que setea el
 * user en localStorage. Uso:
 *
 *     test("…", async ({ page, loginAs }) => {
 *       const user = await loginAs("gklead");
 *       await page.goto("/dashboard");
 *       …
 *     });
 */
export const test = base.extend<{
  loginAs: (roleId: RoleId) => Promise<E2EUser>;
}>({
  loginAs: async ({ page }, use) => {
    await use((roleId) => seedUser(page, roleId));
  },
});

export { expect } from "@playwright/test";

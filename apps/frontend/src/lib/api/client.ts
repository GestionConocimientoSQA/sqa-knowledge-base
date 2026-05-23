import ky from "ky";

import { getCurrentUser } from "@/lib/auth/auth-stub";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * `true` cuando se configuró una URL de API real. En tests (Vitest +
 * Playwright) la env var no está seteada, por lo que `lib/api/*.ts`
 * sigue resolviendo contra los mocks-stub y la suite no necesita backend.
 *
 * En dev local con backend corriendo en `:8000` (1B.5), seteá
 * `NEXT_PUBLIC_API_URL=http://localhost:8000` en `.env.local` y la app
 * habla con PostgreSQL real automáticamente.
 */
export const USE_REAL_API = Boolean(process.env.NEXT_PUBLIC_API_URL);

/**
 * Cliente HTTP base. Inyecta el header `Authorization: Bearer dev:{oid}`
 * leyendo del auth-stub para que el `DevTokenValidator` del backend
 * (Fase 1B.3) lo reconozca. Cuando se haga el swap a MSAL real (Fase 11),
 * acá leemos el JWT real en lugar del bearer fake.
 */
export const api = ky.create({
  prefixUrl: API_URL,
  timeout: 30_000,
  retry: { limit: 2, methods: ["get"] },
  hooks: {
    beforeRequest: [
      (request) => {
        const user = getCurrentUser();
        if (user) {
          request.headers.set("Authorization", `Bearer dev:${user.oid}`);
        }
        request.headers.set("X-Request-ID", crypto.randomUUID());
      },
    ],
  },
});

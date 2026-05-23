/**
 * API de autenticación contra el backend.
 *
 * En modo stub (default sin `NEXT_PUBLIC_API_URL`) los datos del usuario salen
 * de `auth-stub.ts` (localStorage). Cuando se setea la API real, esta función
 * llama a `GET /auth/me` y trae los permisos finos del backend
 * ([[project-roles-capacidades]]) en lugar de inferirlos en el frontend.
 *
 * El swap a MSAL real (Fase 11) no toca este archivo: cambia `auth-stub` por
 * el provider de @azure/msal-react y el bearer en `client.ts` para que use
 * el JWT real en vez de `Bearer dev:{oid}`.
 */
import { api, USE_REAL_API } from "@/lib/api/client";
import { getCurrentUser as getStubUser } from "@/lib/auth/auth-stub";
import type { AuthUser } from "@/types/domain";

/**
 * Respuesta del backend `GET /auth/me`. El backend serializa en camelCase
 * (alias_generator=to_camel) así que coincide con `AuthUser` del frontend
 * salvo los campos extra del dominio (carpetasOwned, permisos finos) que
 * el frontend ignora por ahora.
 */
interface BackendAuthUser extends AuthUser {
  carpetasOwned?: string[];
  puedeGobernarTaxonomia?: boolean;
  puedeAprobarTaxonomia?: boolean;
  puedeVerMetricasGlobales?: boolean;
}

/**
 * Devuelve el usuario autenticado. Con backend real consulta `/auth/me`;
 * sin backend usa el stub local. Útil para hidratar el contexto de auth
 * al montar la app.
 */
export async function fetchCurrentUser(): Promise<AuthUser | null> {
  if (!USE_REAL_API) {
    return getStubUser();
  }
  try {
    const data = await api.get("auth/me").json<BackendAuthUser>();
    return {
      oid: data.oid,
      email: data.email,
      name: data.name,
      roleId: data.roleId,
      isAdmin: data.isAdmin,
    };
  } catch {
    return null;
  }
}

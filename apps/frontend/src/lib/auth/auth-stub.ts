/**
 * Stub de autenticación que simula la API de @azure/msal-react.
 * Persiste el usuario activo en localStorage para sobrevivir refresh.
 * En Fase 11 se reemplaza por MSAL real sin cambiar la interfaz pública.
 */

import { ROLES } from "@/lib/mocks/data";
import type { AuthUser, RoleId } from "@/types/domain";

const STORAGE_KEY = "sqa-kb:auth-user";

export function signIn(roleId: RoleId): AuthUser {
  const r = ROLES[roleId];
  const user: AuthUser = {
    oid: `stub-${roleId}-00000000`,
    email: r.email,
    name: r.name,
    roleId,
    isAdmin: roleId === "gklead" || roleId === "owner",
  };
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
  }
  return user;
}

export function signOut() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(STORAGE_KEY);
  }
}

export function getCurrentUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function isAuthenticated(): boolean {
  return getCurrentUser() !== null;
}

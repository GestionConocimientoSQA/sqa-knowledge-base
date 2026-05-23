"use client";

import * as React from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  getCurrentUser,
  signIn as signInStub,
  signOut as signOutStub,
} from "./auth-stub";
import { fetchCurrentUser } from "@/lib/api/auth";
import { USE_REAL_API } from "@/lib/api/client";
import type { AuthUser, RoleId } from "@/types/domain";

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  signIn: (roleId: RoleId) => void;
  signOut: () => void;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const router = useRouter();

  React.useEffect(() => {
    let cancelled = false;
    const stub = getCurrentUser();
    if (!stub) {
      setIsLoading(false);
      return;
    }
    if (!USE_REAL_API) {
      setUser(stub);
      setIsLoading(false);
      return;
    }
    // Con backend real, revalidamos el bearer contra `/auth/me` para traer
    // los permisos finos auténticos (no solo el `isAdmin` del stub).
    void fetchCurrentUser().then((u) => {
      if (cancelled) return;
      setUser(u ?? stub);
      setIsLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = React.useCallback(
    (roleId: RoleId) => {
      const u = signInStub(roleId);
      setUser(u);
      // En modo backend real podríamos hidratar con `/auth/me`, pero el
      // stub ya provee oid/email/name/role canónicos antes del swap MSAL.
      router.push("/dashboard");
    },
    [router],
  );

  const signOut = React.useCallback(() => {
    signOutStub();
    setUser(null);
    router.push("/login");
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, isLoading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

/**
 * Guard de rutas autenticadas. Redirige a /login si no hay usuario.
 */
export function useRequireAuth() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  React.useEffect(() => {
    if (!isLoading && !user && pathname !== "/login") {
      router.replace("/login");
    }
  }, [user, isLoading, pathname, router]);

  return { user, isLoading };
}

import { describe, it, expect, beforeEach } from "vitest";
import {
  signIn,
  signOut,
  getCurrentUser,
  isAuthenticated,
} from "@/lib/auth/auth-stub";

describe("auth-stub", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("signs in a user and persists in localStorage", () => {
    const user = signIn("gklead");
    expect(user.email).toBe("andres.altamiranda@sqa.co");
    expect(user.isAdmin).toBe(true);
    expect(getCurrentUser()?.oid).toBe(user.oid);
  });

  it("flags non-admin roles correctly", () => {
    const u = signIn("capturador");
    expect(u.isAdmin).toBe(false);
  });

  it("returns null when no session is stored", () => {
    expect(getCurrentUser()).toBeNull();
    expect(isAuthenticated()).toBe(false);
  });

  it("signOut clears the session", () => {
    signIn("curador");
    expect(isAuthenticated()).toBe(true);
    signOut();
    expect(isAuthenticated()).toBe(false);
  });
});

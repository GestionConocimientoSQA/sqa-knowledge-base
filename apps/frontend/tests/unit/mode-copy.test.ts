import { describe, it, expect } from "vitest";
import {
  MODE_COPY,
  ORDERED_MODES,
  isSessionMode,
} from "@/lib/chat/mode-copy";

describe("mode-copy", () => {
  it("ORDERED_MODES contains exactly the three modes in canonical order", () => {
    expect(ORDERED_MODES).toEqual(["captura", "consulta", "ingesta"]);
  });

  it("MODE_COPY has one entry per ordered mode with required fields", () => {
    for (const mode of ORDERED_MODES) {
      const copy = MODE_COPY[mode];
      expect(copy.mode).toBe(mode);
      expect(copy.title.length).toBeGreaterThan(0);
      expect(copy.short.length).toBeGreaterThan(0);
      expect(copy.description.length).toBeGreaterThan(0);
      expect(copy.cta.length).toBeGreaterThan(0);
      expect(["A", "B", "C"]).toContain(copy.letter);
      expect(copy.icon).toBeDefined();
    }
  });

  it("each mode maps to a unique letter A/B/C", () => {
    const letters = ORDERED_MODES.map((m) => MODE_COPY[m].letter);
    expect(new Set(letters).size).toBe(3);
  });

  it("isSessionMode returns true only for valid modes", () => {
    expect(isSessionMode("captura")).toBe(true);
    expect(isSessionMode("consulta")).toBe(true);
    expect(isSessionMode("ingesta")).toBe(true);
  });

  it("isSessionMode rejects invalid values", () => {
    expect(isSessionMode("CAPTURA")).toBe(false);
    expect(isSessionMode("curaduria")).toBe(false);
    expect(isSessionMode("")).toBe(false);
    expect(isSessionMode(null)).toBe(false);
    expect(isSessionMode(undefined)).toBe(false);
    expect(isSessionMode(42)).toBe(false);
  });
});

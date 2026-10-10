import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  THEME_KEY,
  applyTheme,
  resetThemeForTests,
  resolveTheme,
  setThemePreference,
} from "./theme";

function systemPrefers(scheme: "light" | "dark") {
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query: string) =>
      ({
        matches: scheme === "light" && query.includes("light"),
        media: query,
        addEventListener: () => {},
        removeEventListener: () => {},
      }) as unknown as MediaQueryList,
  );
}

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  resetThemeForTests();
});

afterEach(() => vi.restoreAllMocks());

describe("theme preference", () => {
  it("resolves `system` from the operating system and a pinned choice as itself", () => {
    systemPrefers("light");
    expect(resolveTheme("system")).toBe("light");
    expect(resolveTheme("dark")).toBe("dark");
    systemPrefers("dark");
    expect(resolveTheme("system")).toBe("dark");
    expect(resolveTheme("light")).toBe("light");
  });

  it("puts the resolved theme on <html>, where the tokens and the orbs read it", () => {
    systemPrefers("light");
    expect(applyTheme("system")).toBe("light");
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
    applyTheme("dark");
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
  });

  it("stores only the chosen theme, and nothing at all for `system`", () => {
    systemPrefers("dark");
    setThemePreference("light");
    expect(localStorage.getItem(THEME_KEY)).toBe("light");
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
    expect(localStorage.length).toBe(1);
    setThemePreference("system");
    expect(localStorage.getItem(THEME_KEY)).toBeNull();
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
  });

  it("ignores a stored value that is not a theme", () => {
    localStorage.setItem(THEME_KEY, "neon");
    resetThemeForTests();
    systemPrefers("dark");
    expect(applyTheme()).toBe("dark");
  });

  it("keeps working when storage is blocked", () => {
    systemPrefers("dark");
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(() => setThemePreference("light")).not.toThrow();
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
  });
});

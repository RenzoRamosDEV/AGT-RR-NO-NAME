import { useSyncExternalStore } from "react";

export type ThemePreference = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

export const THEME_KEY = "duelo-theme";
const PREFERENCES: readonly ThemePreference[] = ["system", "light", "dark"];

const listeners = new Set<() => void>();
let preference: ThemePreference = readStored();

function readStored(): ThemePreference {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    return PREFERENCES.find((p) => p === stored) ?? "system";
  } catch {
    return "system";
  }
}

function lightQuery(): MediaQueryList | null {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-color-scheme: light)")
    : null;
}

function systemTheme(): ResolvedTheme {
  return lightQuery()?.matches ? "light" : "dark";
}

export function resolveTheme(pref: ThemePreference): ResolvedTheme {
  return pref === "system" ? systemTheme() : pref;
}

/** Puts the resolved theme on <html>: the CSS tokens and the orbs read it from there. */
export function applyTheme(pref: ThemePreference = preference): ResolvedTheme {
  const resolved = resolveTheme(pref);
  document.documentElement.setAttribute("data-theme", resolved);
  return resolved;
}

export function setThemePreference(next: ThemePreference): void {
  preference = next;
  try {
    // Only the preference is stored, never anything about the user or the data.
    if (next === "system") localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, next);
  } catch {
    // Storage may be blocked: the choice then lasts until the page closes.
  }
  applyTheme(next);
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  const query = lightQuery();
  const onSystemChange = () => {
    if (preference === "system") {
      applyTheme("system");
      listener();
    }
  };
  query?.addEventListener?.("change", onSystemChange);
  return () => {
    listeners.delete(listener);
    query?.removeEventListener?.("change", onSystemChange);
  };
}

export function useThemePreference(): [ThemePreference, (next: ThemePreference) => void] {
  const current = useSyncExternalStore(
    subscribe,
    () => preference,
    () => "system" as ThemePreference,
  );
  return [current, setThemePreference];
}

/** The theme actually in force (`system` resolved), for things that need it as a value. */
export function useResolvedTheme(): ResolvedTheme {
  const [pref] = useThemePreference();
  const system = useSyncExternalStore(
    (listener) => {
      const query = lightQuery();
      query?.addEventListener?.("change", listener);
      return () => query?.removeEventListener?.("change", listener);
    },
    systemTheme,
    () => "dark" as ResolvedTheme,
  );
  return pref === "system" ? system : pref;
}

/** Test hook: forget the cached preference and re-read storage. */
export function resetThemeForTests(): void {
  preference = readStored();
}

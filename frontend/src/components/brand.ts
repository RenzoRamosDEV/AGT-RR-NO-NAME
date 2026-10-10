import heroDark from "../assets/brand/hero-dark.webp";
import heroLight from "../assets/brand/hero-light.webp";
import markDark32 from "../assets/brand/mark-dark-32.png";
import markDark64 from "../assets/brand/mark-dark-64.png";
import markDark128 from "../assets/brand/mark-dark-128.png";
import markLight32 from "../assets/brand/mark-light-32.png";
import markLight64 from "../assets/brand/mark-light-64.png";
import markLight128 from "../assets/brand/mark-light-128.png";
import type { ResolvedTheme } from "../lib/theme";

/** One picture per theme: the neon logo suits the dark theme and the 3D one the light theme. */
export interface Themed<T> {
  dark: T;
  light: T;
}

/** Emblem (the two central chat heads) at three pixel densities, for the top bar and small spots. */
export const MARK: Themed<{ 32: string; 64: string; 128: string }> = {
  dark: { 32: markDark32, 64: markDark64, 128: markDark128 },
  light: { 32: markLight32, 64: markLight64, 128: markLight128 },
};

/** Full composition on the card color of each theme, for the empty states and the not-found pages. */
export const HERO: Themed<string> = { dark: heroDark, light: heroLight };

export function pickTheme<T>(themed: Themed<T>, theme: ResolvedTheme): T {
  return theme === "light" ? themed.light : themed.dark;
}

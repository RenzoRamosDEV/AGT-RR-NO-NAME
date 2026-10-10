import { Suspense, lazy } from "react";
import { useThemePreference } from "../lib/theme";
import { useReducedMotion } from "../lib/useReducedMotion";
import { THEME_OPTIONS, ThemeButton } from "./ThemeButton";

// libraries.dev `liquid-gooey`: a separate chunk, so the header is usable before it arrives.
const FluidThemeSwitch = lazy(() => import("./FluidThemeSwitch"));

function StaticThemeSwitch({ compact }: { compact: boolean }) {
  const [preference, setPreference] = useThemePreference();
  return (
    <fieldset className="segmented theme-switch" aria-label={compact ? "Tema (cabecera)" : "Tema"}>
      {THEME_OPTIONS.map((option) => (
        <ThemeButton
          key={option.value}
          option={option}
          compact={compact}
          pressed={preference === option.value}
          onSelect={setPreference}
        />
      ))}
    </fieldset>
  );
}

/**
 * Theme selector (System / Light / Dark), a segmented control of toggle buttons. `compact` keeps
 * only the icons (header); the accessible name always carries the full text.
 *
 * It first paints as a plain segmented control and, once the `liquid-gooey` chunk is in, the
 * active segment becomes a liquid indicator. Under `prefers-reduced-motion` it stays the plain
 * control: the pressed button is simply tinted.
 */
export function ThemeSwitch({ compact = false }: { compact?: boolean }) {
  const reduced = useReducedMotion();
  const plain = <StaticThemeSwitch compact={compact} />;
  if (reduced) return plain;
  return (
    <Suspense fallback={plain}>
      <FluidThemeSwitch compact={compact} />
    </Suspense>
  );
}

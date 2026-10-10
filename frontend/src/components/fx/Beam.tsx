import { type ReactNode, Suspense, lazy } from "react";
import { useResolvedTheme } from "../../lib/theme";
import { useReducedMotion } from "../../lib/useReducedMotion";

// libraries.dev `border-beam`: a separate chunk, fetched only once something is in progress.
const BeamLayer = lazy(() => import("./BeamLayer"));

/**
 * Amber glow that travels along the bottom edge of something that is still in progress (libraries.dev
 * `border-beam`, `line` preset: on a wide row or panel a full-border spot would be a dot, and the
 * pulsing variants only leave a halo outside). It only wraps what is `active` — a finished row costs
 * nothing — and never animates under `prefers-reduced-motion`; the status icon, the badge and the
 * "revisando…" orbs already say "en curso". While the chunk loads the content is shown as it is.
 */
export function Beam({ active, children }: { active: boolean; children: ReactNode }) {
  const reduced = useReducedMotion();
  const theme = useResolvedTheme();
  if (!active || reduced) return <>{children}</>;
  return (
    <Suspense fallback={children}>
      <BeamLayer theme={theme}>{children}</BeamLayer>
    </Suspense>
  );
}

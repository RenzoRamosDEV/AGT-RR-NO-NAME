import { type ComponentProps, Suspense, lazy } from "react";
import { useResolvedTheme } from "../../lib/theme";
import { useReducedMotion } from "../../lib/useReducedMotion";
import { Button } from "../ui/Button";
import { hasWebGL } from "./webgl";

// `metal-fx` (and its shader) is a separate chunk, fetched only where WebGL2 can run it.
const MetalRing = lazy(() => import("./MetalRing"));

/**
 * A `Button` with a liquid-metal ring (libraries.dev `metal-fx`). It is only for the few actions
 * that matter most (adding a project, retrying a review): a ring on every button would be noise.
 *
 * `metal-fx` replaces the button's own fill with its surface (white in the light theme, dark grey
 * in the dark one), so the label cannot be the white-on-green of a primary button: it always uses
 * the neutral look (`btn-metal`: normal text color, semibold), with or without the ring. Without
 * WebGL2, under `prefers-reduced-motion` or while the chunk loads it is that same button, so the
 * layout never jumps.
 */
export function MetalButton({ className = "", ...rest }: ComponentProps<typeof Button>) {
  const reduced = useReducedMotion();
  const theme = useResolvedTheme();
  const plain = <Button {...rest} variant="default" className={`btn-metal ${className}`.trim()} />;
  if (reduced || !hasWebGL(2)) return plain;
  return (
    <Suspense fallback={plain}>
      <MetalRing theme={theme}>{plain}</MetalRing>
    </Suspense>
  );
}

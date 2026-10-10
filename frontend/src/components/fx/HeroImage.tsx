import { Suspense, lazy } from "react";
import { useResolvedTheme } from "../../lib/theme";
import { useReducedMotion } from "../../lib/useReducedMotion";
import { type Themed, pickTheme } from "../brand";
import { hasWebGL } from "./webgl";

// The WebGL effect (and `three`) is a separate chunk, fetched only when it can actually run.
const HeroImageFx = lazy(() => import("./HeroImageFx"));

const WIDTH = 240;
const HEIGHT = 160;

/**
 * Hero picture of an empty state. With WebGL it plays the libraries.dev `img-fx` loader that turns
 * into the picture; without WebGL, under `prefers-reduced-motion` or while the chunk loads, it is
 * the same picture as a plain `<img>`. The art is decorative, so it has no alternative text: the
 * empty state's title and text already say everything. `src` is one picture or a picture per
 * theme (the logo of the theme in force).
 */
export function HeroImage({
  src: source,
  alt = "",
}: { src: string | Themed<string>; alt?: string }) {
  const reduced = useReducedMotion();
  const theme = useResolvedTheme();
  const src = typeof source === "string" ? source : pickTheme(source, theme);
  const still = (
    <img
      className="hero-img"
      data-variant={typeof source === "string" ? undefined : theme}
      src={src}
      alt={alt}
      width={WIDTH}
      height={HEIGHT}
      decoding="async"
    />
  );
  if (reduced || !hasWebGL()) return still;
  return (
    <div className="hero" data-fx="img">
      <Suspense fallback={still}>
        <HeroImageFx src={src} width={WIDTH} height={HEIGHT} />
      </Suspense>
    </div>
  );
}

import { Suspense, lazy } from "react";
import { useReducedMotion } from "../../lib/useReducedMotion";
import { hasWebGL } from "./webgl";

// The WebGL effect (and `three`) is a separate chunk, fetched only when it can actually run.
const HeroImageFx = lazy(() => import("./HeroImageFx"));

const WIDTH = 240;
const HEIGHT = 160;

/**
 * Hero picture of an empty state. With WebGL it plays the libraries.dev `img-fx` loader that turns
 * into the picture; without WebGL, under `prefers-reduced-motion` or while the chunk loads, it is
 * the same picture as a plain `<img>`. The art is decorative, so it has no alternative text: the
 * empty state's title and text already say everything.
 */
export function HeroImage({ src, alt = "" }: { src: string; alt?: string }) {
  const reduced = useReducedMotion();
  const still = (
    <img className="hero-img" src={src} alt={alt} width={WIDTH} height={HEIGHT} decoding="async" />
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

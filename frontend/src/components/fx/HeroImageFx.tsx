import { ImageGeneration } from "img-fx";
import { useMemo } from "react";
import { useResolvedTheme } from "../../lib/theme";

/** The picture stays up (about a day) once revealed: the hero plays one pass, it does not loop. */
const HOLD_FOREVER_MS = 24 * 60 * 60 * 1000;

/**
 * The WebGL half of {@link HeroImage} (libraries.dev `img-fx`). It lives in its own module so that
 * `three` is only downloaded when an empty state is actually shown, never with the main bundle.
 * It plays one pass — the "generating" mosaic, then the picture — and stays on the picture.
 */
export default function HeroImageFx({
  src,
  width,
  height,
}: {
  src: string;
  width: number;
  height: number;
}) {
  const theme = useResolvedTheme();
  // A new array on every render would restart the effect's picture pool.
  const images = useMemo(() => [src], [src]);

  return (
    <ImageGeneration
      preset="pixels-organic"
      theme={theme}
      images={images}
      autoReveal
      revealDelayRange={[1.2, 1.6]}
      revealHoldMs={HOLD_FOREVER_MS}
      pixelScale={1.5}
      strength={0.9}
    >
      <div className="hero-card" style={{ width, height }} />
    </ImageGeneration>
  );
}

import { useResolvedTheme } from "../lib/theme";
import { MARK, pickTheme } from "./brand";

/**
 * The Duelo emblem of the theme in force. The theme comes from `useResolvedTheme`, which applies
 * the same rule as the script in `index.html` that sets `data-theme` before the first paint, and
 * `#root` is empty until React mounts, so the right logo is the first one ever painted. The size
 * is reserved with `width`/`height`, so swapping themes moves nothing.
 *
 * It is decorative by default (the app name is written next to it); pass `decorative={false}` when
 * it stands alone and needs to be announced.
 */
export function BrandLogo({
  size = 28,
  decorative = true,
  className = "",
}: {
  size?: number;
  decorative?: boolean;
  className?: string;
}) {
  const theme = useResolvedTheme();
  const mark = pickTheme(MARK, theme);
  // Up to 32 px: 32 and 64 px files; above that: 64 and 128 px files.
  const small = size <= 32;
  const src = small ? mark[32] : mark[64];
  const srcSet = `${src} 1x, ${small ? mark[64] : mark[128]} 2x`;
  return (
    <img
      className={`brand-logo ${className}`.trim()}
      data-variant={theme}
      src={src}
      srcSet={srcSet}
      alt={decorative ? "" : "Duelo"}
      width={size}
      height={size}
      decoding="async"
    />
  );
}

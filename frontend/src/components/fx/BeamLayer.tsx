import { BorderBeam } from "border-beam";
import type { ReactNode } from "react";
import type { ResolvedTheme } from "../../lib/theme";

/** The `border-beam` half of {@link Beam}, in its own module so the library is fetched on demand. */
export default function BeamLayer({
  theme,
  children,
}: {
  theme: ResolvedTheme;
  children: ReactNode;
}) {
  return (
    <BorderBeam
      className="beam"
      size="line"
      colorVariant="sunset"
      staticColors
      theme={theme}
      strength={theme === "dark" ? 1 : 0.8}
      brightness={1.3}
    >
      {children}
    </BorderBeam>
  );
}

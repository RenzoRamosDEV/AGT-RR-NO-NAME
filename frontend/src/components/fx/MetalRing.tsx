import { MetalFx } from "metal-fx";
import type { ReactNode } from "react";
import type { ResolvedTheme } from "../../lib/theme";

/** The `metal-fx` half of {@link MetalButton}, in its own module so it is fetched only when used. */
export default function MetalRing({
  theme,
  children,
}: {
  theme: ResolvedTheme;
  children: ReactNode;
}) {
  return (
    <MetalFx variant="button" preset="silver" theme={theme} strength={0.85} className="metal">
      {children}
    </MetalFx>
  );
}

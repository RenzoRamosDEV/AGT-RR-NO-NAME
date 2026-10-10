import type { ReactNode } from "react";

/** A GitHub-style label (rounded pill with a tinted background). */
export function Badge({
  tone = "neutral",
  children,
}: {
  tone?: "neutral" | "success" | "danger" | "warning" | "accent" | "done";
  children: ReactNode;
}) {
  return (
    <span className="badge" data-tone={tone}>
      {children}
    </span>
  );
}

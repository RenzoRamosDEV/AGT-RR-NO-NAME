import type { ReactNode } from "react";

/** Simple line illustration shared by the empty, error and not-found states. */
function Illustration({ kind }: { kind: "empty" | "missing" | "error" }) {
  return (
    <svg
      className="empty-art"
      width="96"
      height="72"
      viewBox="0 0 96 72"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <rect x="8" y="10" width="80" height="52" rx="8" stroke="var(--border)" strokeWidth="2" />
      <path d="M8 24h80" stroke="var(--border)" strokeWidth="2" />
      <circle cx="18" cy="17" r="2" fill="var(--border)" />
      <circle cx="26" cy="17" r="2" fill="var(--border)" />
      {kind === "empty" && (
        <>
          <path
            d="M24 38h30M24 48h44"
            stroke="var(--border)"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <circle cx="70" cy="38" r="5" stroke="var(--accent)" strokeWidth="2" />
        </>
      )}
      {kind === "missing" && (
        <path
          d="m40 34 16 16M56 34 40 50"
          stroke="var(--danger)"
          strokeWidth="3"
          strokeLinecap="round"
        />
      )}
      {kind === "error" && (
        <>
          <path d="M48 32v10" stroke="var(--warning)" strokeWidth="3" strokeLinecap="round" />
          <circle cx="48" cy="49" r="2" fill="var(--warning)" />
        </>
      )}
    </svg>
  );
}

/** A framed message with an illustration, a title, an explanation and the main action. */
export function EmptyState({
  kind = "empty",
  title,
  heading = false,
  children,
  action,
  className = "",
}: {
  kind?: "empty" | "missing" | "error";
  title: ReactNode;
  /** The title is the page's `<h1>` (not-found pages) instead of a plain paragraph. */
  heading?: boolean;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  const Title = heading ? "h1" : "p";
  return (
    <div className={`empty-state ${className}`.trim()}>
      <Illustration kind={kind} />
      <Title className="empty-title">{title}</Title>
      {children && <div className="empty-body">{children}</div>}
      {action && <div className="empty-action">{action}</div>}
    </div>
  );
}

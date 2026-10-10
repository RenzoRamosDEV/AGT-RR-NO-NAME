import { type ReactNode, useId, useState } from "react";

/**
 * Which long texts the user has opened. It lives outside React so it survives the page refreshing
 * itself and a component being mounted again; it is capped so a long session cannot grow it
 * without limit (the oldest entry goes first).
 */
const opened = new Map<string, boolean>();
const MAX_REMEMBERED = 500;

function remember(id: string, open: boolean): void {
  opened.delete(id);
  if (open) opened.set(id, true);
  while (opened.size > MAX_REMEMBERED) {
    const oldest = opened.keys().next().value;
    if (oldest === undefined) break;
    opened.delete(oldest);
  }
}

/** Forgets every opened text; for tests. */
export function resetCollapsibleMemory(): void {
  opened.clear();
}

export interface LengthLimit {
  chars: number;
  lines: number;
}

/** Summaries are read in full more often than findings, so they get a longer limit. */
export const SUMMARY_LIMIT: LengthLimit = { chars: 480, lines: 8 };
export const FINDING_LIMIT: LengthLimit = { chars: 320, lines: 6 };

/** Decided by length and not by measuring the DOM: it is the same on every screen and in tests. */
export function isLong(text: string, limit: LengthLimit): boolean {
  return text.length > limit.chars || text.split("\n").length > limit.lines;
}

/**
 * Shows `children` folded (limited height with a fade and a «Ver más» button) when `long`, and as
 * they are otherwise. `id` must be stable across refreshes: it is the key under which the opened
 * state is remembered.
 */
export function Collapsible({
  id,
  long,
  children,
}: {
  id: string;
  long: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(() => opened.get(id) === true);
  const regionId = useId();
  if (!long) return <>{children}</>;
  return (
    <div className="collapsible" data-open={open ? "true" : "false"}>
      <div className="collapsible-body" id={regionId}>
        {children}
      </div>
      <button
        type="button"
        className="collapsible-toggle"
        aria-expanded={open}
        aria-controls={regionId}
        onClick={() => {
          remember(id, !open);
          setOpen(!open);
        }}
      >
        {open ? "Ver menos" : "Ver más"}
      </button>
    </div>
  );
}

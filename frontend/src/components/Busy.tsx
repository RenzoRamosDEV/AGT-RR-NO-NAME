import { type OrbState, ThinkingOrb } from "thinking-orbs";
import { useResolvedTheme } from "../lib/theme";
import { useReducedMotion } from "../lib/useReducedMotion";

/** What the interface is doing; each activity has one orb state so the meaning lives in one place. */
export type Activity = "load" | "more" | "agent" | "retry" | "connect";

export const ACTIVITY_STATE: Record<Activity, OrbState> = {
  load: "searching",
  more: "working",
  agent: "working",
  retry: "solving",
  connect: "connecting",
};

const ORB_SIZE = 20;

interface Props {
  activity: Activity;
  /** Visible text; it is also what assistive technology announces (the orb is decorative). */
  label: string;
  /** A plain `<span>` for buttons and lists; by default a polite status region. */
  inline?: boolean;
  className?: string;
}

/**
 * Loading / in-progress indicator: a 20 px `thinking-orb` next to a text label. The orb sits in a
 * fixed 20 px slot, so showing or hiding it never moves the layout. Under reduced motion no canvas
 * is mounted: a static "…" takes its place.
 */
export function Busy({ activity, label, inline = false, className = "" }: Props) {
  const reduced = useReducedMotion();
  const theme = useResolvedTheme();
  const cls = ["busy", className].filter(Boolean).join(" ");
  const content = (
    <>
      <span className="busy-orb" aria-hidden="true" data-activity={activity}>
        {reduced ? (
          "…"
        ) : (
          <ThinkingOrb state={ACTIVITY_STATE[activity]} size={ORB_SIZE} theme={theme} />
        )}
      </span>
      <span>{label}</span>
    </>
  );
  if (inline) return <span className={cls}>{content}</span>;
  return (
    <output className={cls} aria-live="polite">
      {content}
    </output>
  );
}

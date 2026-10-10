import { useEffect, useState } from "react";
import { updatedAgo } from "../lib/liveness";
import { usePollMs } from "../lib/polling";

/**
 * Discreet "Actualizado hace N s" for a live page. It ticks on its own timer (paused while the tab
 * is hidden) so the list around it never re-renders, and it is not a live region: only the static
 * failure notice is announced, once, when a background refresh fails.
 */
export function UpdatedAgo({
  updatedAt,
  failed,
}: {
  updatedAt: number | null;
  failed: boolean;
}) {
  const live = usePollMs() > 0;
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!live) return;
    const tick = () => {
      if (document.visibilityState !== "hidden") setNow(Date.now());
    };
    const timer = setInterval(tick, 1000);
    document.addEventListener("visibilitychange", tick);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [live]);

  if (!live || updatedAt === null) return null;
  return (
    <span className="updated muted">
      {failed && <output>No se pudo actualizar; se reintentará. </output>}
      <span>{updatedAgo(Math.max(0, (now - updatedAt) / 1000))}</span>
    </span>
  );
}

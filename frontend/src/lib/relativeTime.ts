const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;
const MAX_RELATIVE_DAYS = 30;

/**
 * "hace 12 min" style age of an ISO timestamp relative to `now` (injected so tests are
 * deterministic). Returns `null` for an invalid date and "hace un momento" for under a minute or a
 * date in the future (clock skew); after 30 days it falls back to the local date.
 */
export function relativeTime(iso: string, now: Date): string | null {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return null;
  const elapsed = now.getTime() - then;
  if (elapsed < MINUTE) return "hace un momento";
  if (elapsed < HOUR) return `hace ${Math.floor(elapsed / MINUTE)} min`;
  if (elapsed < DAY) return `hace ${Math.floor(elapsed / HOUR)} h`;
  const days = Math.floor(elapsed / DAY);
  if (days <= MAX_RELATIVE_DAYS) return `hace ${days} ${days === 1 ? "día" : "días"}`;
  return new Date(then).toLocaleDateString("es-ES");
}

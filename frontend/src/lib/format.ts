const NO_DATA = "—";

const decimal = (value: number) => String(value).replace(".", ",");

/** "—" when unknown, otherwise `850 ms`, `4,2 s`, `42 s` or `2 min 5 s`. */
export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || !Number.isFinite(ms) || ms < 0) return NO_DATA;
  if (ms < 1000) return `${Math.round(ms)} ms`;
  const seconds = Math.round(ms / 100) / 10;
  if (seconds < 10) return `${decimal(seconds)} s`;
  const whole = Math.round(ms / 1000);
  if (whole < 60) return `${whole} s`;
  const rest = whole % 60;
  return rest === 0 ? `${Math.floor(whole / 60)} min` : `${Math.floor(whole / 60)} min ${rest} s`;
}

/** "—" when unknown, otherwise the number with at most one decimal (`8`, `4,1`). */
export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined || !Number.isFinite(score)) return NO_DATA;
  return decimal(Math.round(score * 10) / 10);
}

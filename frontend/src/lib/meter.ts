/** Proportion of `value` over `max` as a percentage clamped to 0-100; 0 when max is not positive. */
export function ratio(value: number, max: number): number {
  if (!(max > 0) || !(value > 0)) return 0;
  return Math.min(100, (value / max) * 100);
}

export type SortDirection = "ascending" | "descending";

/**
 * Returns a sorted copy of `rows` by `key`. Numbers compare as numbers, anything else with
 * `localeCompare`; the sort is stable so equal rows keep their original order in both directions.
 */
export function sortRows<T, K extends keyof T>(
  rows: readonly T[],
  key: K,
  direction: SortDirection,
): T[] {
  const sign = direction === "ascending" ? 1 : -1;
  return rows
    .map((row, index) => ({ row, index }))
    .sort((a, b) => {
      const x = a.row[key];
      const y = b.row[key];
      const order =
        typeof x === "number" && typeof y === "number"
          ? x - y
          : String(x).localeCompare(String(y), "es", { numeric: true });
      return order !== 0 ? sign * order : a.index - b.index;
    })
    .map(({ row }) => row);
}

/** Next sort state when a header is pressed: same column flips the direction, a new one starts ascending. */
export function nextSort<K>(
  current: { key: K; direction: SortDirection } | null,
  key: K,
): { key: K; direction: SortDirection } {
  if (current?.key === key) {
    return { key, direction: current.direction === "ascending" ? "descending" : "ascending" };
  }
  return { key, direction: "ascending" };
}

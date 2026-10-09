/** Appends `incoming` to `existing`, skipping items whose `id` is already present. */
export function mergeUnique<T extends { id: string }>(existing: T[], incoming: T[]): T[] {
  const seen = new Set(existing.map((item) => item.id));
  const fresh: T[] = [];
  for (const item of incoming) {
    if (seen.has(item.id)) continue;
    seen.add(item.id);
    fresh.push(item);
  }
  return [...existing, ...fresh];
}

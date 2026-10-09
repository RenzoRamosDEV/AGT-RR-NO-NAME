import type { Change } from "../data/mock";

/** Case-insensitive substring match on title, author or SHA; blank query matches all. */
export function matchesQuery(change: Change, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return [change.title, change.author, change.sha].some((v) => v.toLowerCase().includes(q));
}

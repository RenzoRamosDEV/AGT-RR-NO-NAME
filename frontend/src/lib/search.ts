import type { Change } from "../data/mock";

/** Case-insensitive substring match on title, author, SHA or ref (the same rule as the server's `q`); blank query matches all. */
export function matchesQuery(change: Change, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return [change.title, change.author, change.sha, change.ref].some((v) =>
    v.toLowerCase().includes(q),
  );
}

import type { Change } from "../data/mock";

export type StateFilter = "all" | "running" | "failed" | "completed";

/**
 * Filters are not exclusive: a change with one running and one failed review matches both
 * "running" and "failed". A change without review data (API listing) only matches "all".
 */
export function matchesState(change: Change, filter: StateFilter): boolean {
  if (filter === "all") return true;
  const reviews = change.reviews;
  if (!reviews || reviews.length === 0) return false;
  if (filter === "completed") return reviews.every((r) => r.status === "completed");
  return reviews.some((r) => r.status === filter);
}

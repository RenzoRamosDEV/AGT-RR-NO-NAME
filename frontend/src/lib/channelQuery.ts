import type { ReviewAggregate } from "../data/mock";

/** The channel's review-state filter as the user sees it. */
export type StateFilter = "all" | "running" | "failed" | "completed";

const STATUSES: Record<Exclude<StateFilter, "all">, ReviewAggregate[]> = {
  running: ["pending", "running"],
  failed: ["failed", "partial_failed"],
  completed: ["completed"],
};

/** Server-side `status` values for a UI filter; `undefined` for "all" (no `status` sent). */
export function statusesFor(filter: StateFilter): ReviewAggregate[] | undefined {
  return filter === "all" ? undefined : STATUSES[filter];
}

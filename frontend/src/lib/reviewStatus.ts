import type { Review, ReviewAggregate } from "../data/mock";

/** Agents that review every change (`agent_names` in the backend configuration). */
export const EXPECTED_AGENTS = 2;

/**
 * Mirrors the backend's `review_status` for the sample data. A review still `running` has no
 * counterpart in the API (only finished reviews are stored), so it makes the change `running`.
 */
export function aggregateStatus(
  reviews: readonly Review[],
  expected: number = EXPECTED_AGENTS,
): ReviewAggregate {
  if (reviews.some((r) => r.status === "running")) return "running";
  const failed = reviews.filter((r) => r.status === "failed").length;
  const total = reviews.length;
  if (total === 0) return "pending";
  if (total < expected) return "running";
  if (failed === 0) return "completed";
  return failed === total ? "failed" : "partial_failed";
}

/** States from which the backend accepts a retry. */
export function isRetryable(status: ReviewAggregate | undefined): boolean {
  return status === "failed" || status === "partial_failed";
}

export const AGGREGATE_LABEL: Record<ReviewAggregate, string> = {
  pending: "Pendiente",
  running: "En curso",
  partial_failed: "Fallo parcial",
  failed: "Fallida",
  completed: "Completada",
};

export const AGGREGATE_TONE: Record<ReviewAggregate, "neutral" | "success" | "danger" | "warning"> =
  {
    pending: "neutral",
    running: "neutral",
    partial_failed: "warning",
    failed: "danger",
    completed: "success",
  };

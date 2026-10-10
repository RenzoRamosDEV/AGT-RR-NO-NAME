import type { Change, ReviewAggregate } from "../data/mock";
import { splitRuns } from "./runs";

/** A change in these states is still waiting for reviews. */
export function isWaiting(status: ReviewAggregate | undefined): boolean {
  return status === "pending" || status === "running";
}

/**
 * Agents a change is still waiting for. With the real API a review that is not finished is not
 * stored, so "reviewing" can only be inferred: a `pending`/`running` change waits for every
 * configured agent that has no review of its CURRENT run (a review of an earlier run does not
 * count; a retry starts them all again). `null` when the agents are not known yet but reviews
 * are still expected, so the caller does not invent names.
 */
export function pendingAgents(
  change: Pick<Change, "reviewStatus" | "reviews" | "run">,
  agentNames: readonly string[] | null,
): readonly string[] | null {
  if (!isWaiting(change.reviewStatus)) return [];
  if (agentNames === null || agentNames.length === 0) return null;
  const { current } = splitRuns(change.reviews ?? [], change.run);
  const delivered = new Set(current.map((review) => review.agent));
  return agentNames.filter((agent) => !delivered.has(agent));
}

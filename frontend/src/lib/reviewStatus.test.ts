import { describe, expect, it } from "vitest";
import type { ReviewStatus } from "../data/mock";
import { makeReview } from "../test/fixtures";
import { aggregateStatus, isRetryable } from "./reviewStatus";

const reviews = (...statuses: ReviewStatus[]) => statuses.map((status) => makeReview({ status }));

describe("aggregateStatus", () => {
  it.each([
    [[], "pending"],
    [["completed"], "running"],
    [["failed"], "running"],
    [["completed", "completed"], "completed"],
    [["failed", "failed"], "failed"],
    [["completed", "failed"], "partial_failed"],
    [["completed", "running"], "running"],
    [["running", "running"], "running"],
  ] as [ReviewStatus[], string][])("%j -> %s", (statuses, expected) => {
    expect(aggregateStatus(reviews(...statuses))).toBe(expected);
  });

  it("uses the number of expected agents", () => {
    expect(aggregateStatus(reviews("completed"), 1)).toBe("completed");
    expect(aggregateStatus(reviews("completed", "completed"), 3)).toBe("running");
  });
});

describe("isRetryable", () => {
  it("only accepts failed and partial_failed", () => {
    expect(
      ["pending", "running", "completed", undefined].map((s) => isRetryable(s as never)),
    ).toEqual([false, false, false, false]);
    expect(isRetryable("failed")).toBe(true);
    expect(isRetryable("partial_failed")).toBe(true);
  });
});

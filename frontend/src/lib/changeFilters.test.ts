import { describe, expect, it } from "vitest";
import { makeChange, makeReview } from "../test/fixtures";
import { matchesState } from "./changeFilters";

const running = makeReview({ status: "running" });
const failed = makeReview({ status: "failed" });
const done = makeReview({ status: "completed" });

describe("matchesState", () => {
  it("matches everything for 'all', even without review data", () => {
    expect(matchesState(makeChange({ reviews: undefined }), "all")).toBe(true);
    expect(matchesState(makeChange({ reviews: [] }), "all")).toBe(true);
  });

  it("matches running and failed when any review has that status", () => {
    const mixed = makeChange({ reviews: [running, failed, done] });
    expect(matchesState(mixed, "running")).toBe(true);
    expect(matchesState(mixed, "failed")).toBe(true);
    expect(matchesState(mixed, "completed")).toBe(false);
  });

  it("matches completed only when every review is completed", () => {
    expect(matchesState(makeChange({ reviews: [done, done] }), "completed")).toBe(true);
    expect(matchesState(makeChange({ reviews: [done, failed] }), "completed")).toBe(false);
  });

  it("does not invent a state for changes without reviews", () => {
    for (const reviews of [undefined, []]) {
      for (const f of ["running", "failed", "completed"] as const) {
        expect(matchesState(makeChange({ reviews }), f)).toBe(false);
      }
    }
  });
});

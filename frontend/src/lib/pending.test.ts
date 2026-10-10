import { describe, expect, it } from "vitest";
import type { ReviewAggregate } from "../data/mock";
import { makeReview } from "../test/fixtures";
import { isWaiting, pendingAgents } from "./pending";

const AGENTS = ["agent_1", "agent_2"];
const change = (
  reviewStatus: ReviewAggregate,
  reviews: ReturnType<typeof makeReview>[] = [],
  run = 1,
) => ({ reviewStatus, reviews, run });

describe("pendingAgents", () => {
  it("waits for every configured agent while nothing has arrived", () => {
    expect(pendingAgents(change("pending"), AGENTS)).toEqual(AGENTS);
  });

  it("stops waiting for an agent as soon as its review arrives", () => {
    const one = makeReview({ agent: "agent_1", run: 1 });
    expect(pendingAgents(change("running", [one]), AGENTS)).toEqual(["agent_2"]);
    const both = [one, makeReview({ agent: "agent_2", run: 1 })];
    expect(pendingAgents(change("running", both), AGENTS)).toEqual([]);
  });

  it("counts a failed review as delivered", () => {
    const failed = makeReview({ agent: "agent_1", status: "failed", run: 1 });
    expect(pendingAgents(change("running", [failed]), AGENTS)).toEqual(["agent_2"]);
  });

  it("does not count a review of an earlier run: a retry waits for everyone again", () => {
    const old = AGENTS.map((agent) => makeReview({ agent, run: 1 }));
    expect(pendingAgents(change("pending", old, 2), AGENTS)).toEqual(AGENTS);
    const fresh = makeReview({ agent: "agent_2", run: 2 });
    expect(pendingAgents(change("running", [...old, fresh], 2), AGENTS)).toEqual(["agent_1"]);
  });

  it("treats a review without run as run 1", () => {
    const legacy = makeReview({ agent: "agent_1" });
    expect(pendingAgents(change("running", [legacy]), AGENTS)).toEqual(["agent_2"]);
  });

  it.each<ReviewAggregate>(["completed", "failed", "partial_failed"])(
    "waits for nobody when the change is %s",
    (status) => {
      expect(pendingAgents(change(status), AGENTS)).toEqual([]);
    },
  );

  it("does not wait on a change whose status is unknown", () => {
    expect(pendingAgents({ reviews: [], run: 1 }, AGENTS)).toEqual([]);
  });

  it("returns null, not invented names, while the agents are unknown", () => {
    expect(pendingAgents(change("pending"), null)).toBeNull();
    expect(pendingAgents(change("running"), [])).toBeNull();
    expect(pendingAgents(change("completed"), null)).toEqual([]);
  });
});

describe("isWaiting", () => {
  it.each<[ReviewAggregate | undefined, boolean]>([
    ["pending", true],
    ["running", true],
    ["completed", false],
    ["failed", false],
    ["partial_failed", false],
    [undefined, false],
  ])("%s -> %s", (status, expected) => {
    expect(isWaiting(status)).toBe(expected);
  });
});

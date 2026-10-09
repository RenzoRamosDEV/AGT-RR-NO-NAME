import { describe, expect, it } from "vitest";
import { makeFinding, makeReview } from "../test/fixtures";
import { groupFindings, severityRank } from "./findings";

describe("severityRank", () => {
  it("orders known severities and sends unknown ones last", () => {
    expect(severityRank("critical")).toBeLessThan(severityRank("HIGH"));
    expect(severityRank("info")).toBeLessThan(severityRank("nit"));
  });
});

describe("groupFindings", () => {
  it("returns no groups without findings", () => {
    expect(groupFindings([makeReview(), makeReview({ findings: [] })])).toEqual([]);
  });

  it("puts findings of different agents in the same file group, most severe first", () => {
    const groups = groupFindings([
      makeReview({
        agent: "claude",
        findings: [makeFinding({ file: "a.py", severity: "low", line: 1, message: "low" })],
      }),
      makeReview({
        agent: "codex",
        findings: [makeFinding({ file: "a.py", severity: "high", line: 9, message: "high" })],
      }),
    ]);
    expect(groups).toHaveLength(1);
    expect(groups[0].findings.map((f) => [f.message, f.agent])).toEqual([
      ["high", "codex"],
      ["low", "claude"],
    ]);
  });

  it("orders by line within the same severity and by file between groups", () => {
    const groups = groupFindings([
      makeReview({
        findings: [
          makeFinding({ file: "b.py", line: 2 }),
          makeFinding({ file: "a.py", line: 7, message: "later" }),
          makeFinding({ file: "a.py", line: 3, message: "earlier" }),
        ],
      }),
    ]);
    expect(groups.map((g) => g.file)).toEqual(["a.py", "b.py"]);
    expect(groups[0].findings.map((f) => f.message)).toEqual(["earlier", "later"]);
  });

  it("gives every finding a unique key even when two reviews report the same thing", () => {
    const same = [makeFinding()];
    const groups = groupFindings([makeReview({ findings: same }), makeReview({ findings: same })]);
    const keys = groups[0].findings.map((f) => f.key);
    expect(new Set(keys).size).toBe(2);
  });
});

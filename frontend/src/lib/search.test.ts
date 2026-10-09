import { describe, expect, it } from "vitest";
import type { Change } from "../data/mock";
import { matchesQuery } from "./search";

const change: Change = {
  id: "c1",
  kind: "commit",
  title: "Fix: Token compare",
  author: "Renzo",
  sha: "a41f9c2",
  diff: "",
  reviews: [],
};

describe("matchesQuery", () => {
  it.each([
    ["", true],
    ["   ", true],
    ["token", true],
    ["RENZO", true],
    ["41F9", true],
    ["zzz", false],
  ])("query %j -> %s", (query, expected) => {
    expect(matchesQuery(change, query)).toBe(expected);
  });
});

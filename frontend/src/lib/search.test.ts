import { describe, expect, it } from "vitest";
import { makeChange } from "../test/fixtures";
import { matchesQuery } from "./search";

const change = makeChange({
  id: "c1",
  title: "Fix: Token compare",
  author: "Renzo",
  sha: "a41f9c2",
});

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

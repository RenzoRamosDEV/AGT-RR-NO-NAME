import { describe, expect, it } from "vitest";
import { formatDuration, formatScore } from "./format";

describe("formatDuration", () => {
  it.each([
    [null, "—"],
    [undefined, "—"],
    [-1, "—"],
    [Number.NaN, "—"],
    [0, "0 ms"],
    [850, "850 ms"],
    [999.4, "999 ms"],
    [1000, "1 s"],
    [4200, "4,2 s"],
    [9949, "9,9 s"],
    [10_000, "10 s"],
    [42_000, "42 s"],
    [59_400, "59 s"],
    [60_000, "1 min"],
    [125_000, "2 min 5 s"],
  ])("%s -> %s", (ms, expected) => {
    expect(formatDuration(ms as number | null | undefined)).toBe(expected);
  });
});

describe("formatScore", () => {
  it.each([
    [null, "—"],
    [undefined, "—"],
    [8, "8"],
    [4.1, "4,1"],
    [3.84, "3,8"],
    [0, "0"],
  ])("%s -> %s", (score, expected) => {
    expect(formatScore(score as number | null | undefined)).toBe(expected);
  });
});

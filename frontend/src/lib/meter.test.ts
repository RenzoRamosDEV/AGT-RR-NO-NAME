import { describe, expect, it } from "vitest";
import { ratio } from "./meter";

describe("ratio", () => {
  it.each([
    [5, 10, 50],
    [10, 10, 100],
    [15, 10, 100],
    [0, 10, 0],
    [-3, 10, 0],
    [5, 0, 0],
    [Number.NaN, 10, 0],
  ])("ratio(%s, %s) = %s", (value, max, expected) => {
    expect(ratio(value, max)).toBe(expected);
  });
});

import { describe, expect, it } from "vitest";
import { nextSort, sortRows } from "./sort";

const rows = [
  { name: "b", n: 2 },
  { name: "a", n: 10 },
  { name: "c", n: 2 },
];

describe("sortRows", () => {
  it("sorts numbers numerically, not as text", () => {
    expect(sortRows(rows, "n", "ascending").map((r) => r.n)).toEqual([2, 2, 10]);
  });

  it("sorts text ascending and descending", () => {
    expect(sortRows(rows, "name", "ascending").map((r) => r.name)).toEqual(["a", "b", "c"]);
    expect(sortRows(rows, "name", "descending").map((r) => r.name)).toEqual(["c", "b", "a"]);
  });

  it("is stable for equal values in both directions", () => {
    expect(sortRows(rows, "n", "ascending").map((r) => r.name)).toEqual(["b", "c", "a"]);
    expect(sortRows(rows, "n", "descending").map((r) => r.name)).toEqual(["a", "b", "c"]);
  });

  it("puts missing values last in both directions, keeping their order", () => {
    const data = [
      { name: "x", n: null },
      { name: "a", n: 3 },
      { name: "y", n: undefined },
      { name: "b", n: 1 },
    ];
    expect(sortRows(data, "n", "ascending").map((r) => r.name)).toEqual(["b", "a", "x", "y"]);
    expect(sortRows(data, "n", "descending").map((r) => r.name)).toEqual(["a", "b", "x", "y"]);
  });

  it("does not mutate the input", () => {
    const copy = [...rows];
    sortRows(rows, "n", "descending");
    expect(rows).toEqual(copy);
  });
});

describe("nextSort", () => {
  it("starts ascending on a new column and flips on the same one", () => {
    const first = nextSort(null, "n");
    expect(first).toEqual({ key: "n", direction: "ascending" });
    expect(nextSort(first, "n").direction).toBe("descending");
    expect(nextSort(nextSort(first, "n"), "n").direction).toBe("ascending");
    expect(nextSort(first, "name")).toEqual({ key: "name", direction: "ascending" });
  });
});

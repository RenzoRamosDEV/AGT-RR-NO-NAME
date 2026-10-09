import { describe, expect, it } from "vitest";
import { mergeUnique } from "./pagination";

describe("mergeUnique", () => {
  it("appends new items in order", () => {
    expect(mergeUnique([{ id: "a" }], [{ id: "b" }, { id: "c" }]).map((i) => i.id)).toEqual([
      "a",
      "b",
      "c",
    ]);
  });

  it("drops items already present and duplicates inside the incoming page", () => {
    const merged = mergeUnique([{ id: "a" }, { id: "b" }], [{ id: "b" }, { id: "c" }, { id: "c" }]);
    expect(merged.map((i) => i.id)).toEqual(["a", "b", "c"]);
  });

  it("does not mutate its inputs", () => {
    const existing = [{ id: "a" }];
    mergeUnique(existing, [{ id: "b" }]);
    expect(existing).toHaveLength(1);
  });
});

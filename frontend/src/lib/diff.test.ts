import { describe, expect, it } from "vitest";
import { parseDiff } from "./diff";

describe("parseDiff", () => {
  it("numbers old and new lines independently", () => {
    const rows = parseDiff("@@ src/a.py\n-a\n+b\n+c\n ctx");
    expect(rows.map((r) => [r.kind, r.oldNo, r.newNo])).toEqual([
      ["header", undefined, undefined],
      ["del", 1, undefined],
      ["add", undefined, 1],
      ["add", undefined, 2],
      ["context", 2, 3],
    ]);
  });

  it("honours hunk ranges", () => {
    const rows = parseDiff("@@ -10,2 +20,3 @@\n x\n+y");
    expect(rows[1]).toMatchObject({ kind: "context", oldNo: 10, newNo: 20 });
    expect(rows[2]).toMatchObject({ kind: "add", newNo: 21 });
  });

  it("restarts numbering on each header", () => {
    const rows = parseDiff("@@ a\n+x\n@@ b\n+y");
    expect(rows.filter((r) => r.kind === "add").map((r) => r.newNo)).toEqual([1, 1]);
  });

  it("gives every row a unique id even with repeated text", () => {
    const rows = parseDiff("+same\n+same");
    expect(new Set(rows.map((r) => r.id)).size).toBe(2);
  });
});

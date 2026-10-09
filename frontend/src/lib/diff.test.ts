import { describe, expect, it } from "vitest";
import { UNNAMED_FILE, diffFiles, parseDiff } from "./diff";

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

describe("parseDiff headers", () => {
  const GIT = [
    "diff --git a/src/x.py b/src/x.py",
    "index 111..222 100644",
    "--- a/src/x.py",
    "+++ b/src/x.py",
    "@@ -5,2 +5,3 @@",
    " keep",
    "-old",
    "+new",
    "+extra",
  ].join("\n");

  it("treats git metadata as metadata, not as changes", () => {
    const rows = parseDiff(GIT);
    expect(rows.map((r) => r.kind)).toEqual([
      "header",
      "meta",
      "meta",
      "meta",
      "header",
      "context",
      "del",
      "add",
      "add",
    ]);
    expect(rows[0].file).toBe("src/x.py");
    expect(rows[5]).toMatchObject({ oldNo: 5, newNo: 5 });
  });

  it("counts a deleted line starting with dashes inside a hunk", () => {
    const rows = parseDiff("diff --git a/a b/a\n@@ -1,1 +1,0 @@\n--- comment");
    expect(rows[2]).toMatchObject({ kind: "del", oldNo: 1 });
  });

  it("marks file headers but not hunk headers", () => {
    const rows = parseDiff("@@ a.py\n+x\n@@ -1,1 +1,2 @@\n+y");
    expect(rows.map((r) => r.file)).toEqual(["a.py", undefined, undefined, undefined]);
  });
});

describe("diffFiles", () => {
  it("counts additions and deletions per file", () => {
    const files = diffFiles(parseDiff("@@ a.py\n-a\n+b\n+c\n@@ b.py\n+x"));
    expect(files).toEqual([
      { name: "a.py", additions: 2, deletions: 1, rowId: 0 },
      { name: "b.py", additions: 1, deletions: 0, rowId: 4 },
    ]);
  });

  it("does not count git metadata in the totals", () => {
    const files = diffFiles(
      parseDiff("diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1,1 +1,2 @@\n ctx\n+n"),
    );
    expect(files).toEqual([{ name: "x", additions: 1, deletions: 0, rowId: 0 }]);
  });

  it("groups a hunk-only diff under an unnamed file", () => {
    const files = diffFiles(parseDiff("@@ -1,1 +1,2 @@\n ctx\n+n"));
    expect(files).toEqual([{ name: UNNAMED_FILE, additions: 1, deletions: 0, rowId: 0 }]);
  });

  it("returns no files for an empty diff", () => {
    expect(diffFiles(parseDiff(""))).toEqual([]);
  });
});

export type DiffRowKind = "header" | "add" | "del" | "context";

export interface DiffRow {
  id: number;
  kind: DiffRowKind;
  text: string;
  oldNo?: number;
  newNo?: number;
}

const HUNK = /^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/;

/**
 * Parses a unified-style diff into numbered rows. A `@@ -a,b +c,d @@` header sets the counters;
 * any other `@@ <file>` header is shown as a file header and restarts both counters at 1.
 */
export function parseDiff(diff: string): DiffRow[] {
  let oldNo = 1;
  let newNo = 1;
  return diff.split("\n").map((text, id): DiffRow => {
    if (text.startsWith("@@")) {
      const m = HUNK.exec(text);
      oldNo = m ? Number(m[1]) : 1;
      newNo = m ? Number(m[2]) : 1;
      return { id, kind: "header", text };
    }
    if (text.startsWith("+")) return { id, kind: "add", text, newNo: newNo++ };
    if (text.startsWith("-")) return { id, kind: "del", text, oldNo: oldNo++ };
    return { id, kind: "context", text, oldNo: oldNo++, newNo: newNo++ };
  });
}

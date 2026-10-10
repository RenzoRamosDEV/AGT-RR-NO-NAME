export type DiffRowKind = "header" | "meta" | "add" | "del" | "context";

export interface DiffRow {
  id: number;
  kind: DiffRowKind;
  text: string;
  oldNo?: number;
  newNo?: number;
  /** Set on the header row that starts a file (`@@ <file>` or `diff --git`). */
  file?: string;
}

export interface DiffFile {
  name: string;
  additions: number;
  deletions: number;
  /** Id of the row where the file starts; the page anchors the section on it. */
  rowId: number;
}

export const UNNAMED_FILE = "(sin nombre)";

const HUNK = /^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/;
const GIT_HEADER = /^diff --git a\/.+? b\/(.+)$/;

function gitFileName(line: string): string {
  const m = GIT_HEADER.exec(line);
  return m ? m[1] : line.slice("diff --git ".length).trim() || UNNAMED_FILE;
}

/**
 * Parses a unified-style diff into numbered rows. Understands three header shapes:
 * `@@ -a,b +c,d @@` (hunk, sets the counters), `@@ <file>` (file header, restarts both counters
 * at 1) and git's `diff --git` block, whose `index`/`---`/`+++` lines are metadata, not changes.
 * Metadata is only recognised between `diff --git` and the first hunk, so a deleted line that
 * happens to start with `--` inside a hunk still counts as a deletion.
 */
export function parseDiff(diff: string): DiffRow[] {
  let oldNo = 1;
  let newNo = 1;
  let inGitHeader = false;
  return diff.split("\n").map((text, id): DiffRow => {
    if (text.startsWith("diff --git ")) {
      inGitHeader = true;
      oldNo = 1;
      newNo = 1;
      return { id, kind: "header", text, file: gitFileName(text) };
    }
    if (text.startsWith("@@")) {
      inGitHeader = false;
      const m = HUNK.exec(text);
      oldNo = m ? Number(m[1]) : 1;
      newNo = m ? Number(m[2]) : 1;
      return m
        ? { id, kind: "header", text }
        : { id, kind: "header", text, file: text.slice(2).trim() || UNNAMED_FILE };
    }
    if (inGitHeader) return { id, kind: "meta", text };
    if (text.startsWith("+")) return { id, kind: "add", text, newNo: newNo++ };
    if (text.startsWith("-")) return { id, kind: "del", text, oldNo: oldNo++ };
    return { id, kind: "context", text, oldNo: oldNo++, newNo: newNo++ };
  });
}

/**
 * Groups rows by file with added/deleted counts. A diff with changes but no file header (only
 * hunks) yields a single unnamed file so the counts are not lost.
 */
export function diffFiles(rows: DiffRow[]): DiffFile[] {
  const files: DiffFile[] = [];
  let current: DiffFile | undefined;
  for (const row of rows) {
    if (row.file !== undefined) {
      current = { name: row.file, additions: 0, deletions: 0, rowId: row.id };
      files.push(current);
    } else if (row.kind === "header" || row.kind === "add" || row.kind === "del") {
      current ??=
        files[files.push({ name: UNNAMED_FILE, additions: 0, deletions: 0, rowId: row.id }) - 1];
      if (row.kind === "add") current.additions += 1;
      if (row.kind === "del") current.deletions += 1;
    }
  }
  return files;
}

/**
 * GitHub's five-square bar for a file: how many squares are additions, deletions and neutral.
 * With changes, a side that has any gets at least one square; the total is always 5.
 */
export function diffSquares(
  additions: number,
  deletions: number,
): { add: number; del: number; neutral: number } {
  const total = additions + deletions;
  if (total === 0) return { add: 0, del: 0, neutral: 5 };
  let add = Math.round((additions / total) * 5);
  if (additions > 0 && add === 0) add = 1;
  if (deletions > 0 && add === 5) add = 4;
  return { add, del: 5 - add, neutral: 0 };
}

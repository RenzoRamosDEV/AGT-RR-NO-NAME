import { describe, expect, it } from "vitest";
import type { Change } from "../data/mock";
import { undoneCounts, undoneNotice } from "./commitState";

type Probe = Pick<Change, "kind" | "commitState" | "revertedBy">;
const commit = (extra: Partial<Probe> = {}): Probe => ({ kind: "commit", ...extra });

describe("undoneNotice", () => {
  it("says a discarded commit is no longer on the branch", () => {
    expect(undoneNotice(commit({ commitState: "discarded" }))).toEqual({
      state: "discarded",
      label: "COMMIT DESHECHO",
      subtitle: "Ya no está en la rama",
    });
  });

  it("names the commit that reverted a reverted one, with a short SHA", () => {
    const notice = undoneNotice(
      commit({
        commitState: "reverted",
        revertedBy: { id: "c5", sha: "d93f0b4aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" },
      }),
    );
    expect(notice).toEqual({
      state: "reverted",
      label: "COMMIT REVERTIDO",
      subtitle: "Revertido por d93f0b4",
    });
  });

  it("still says it is reverted when the reverting commit is not known", () => {
    expect(undoneNotice(commit({ commitState: "reverted" }))?.subtitle).toBe(
      "Revertido por otro commit",
    );
  });

  it.each([undefined, "active" as const])("is null for a normal commit (%s)", (state) => {
    expect(undoneNotice(commit({ commitState: state }))).toBeNull();
  });

  it.each(["discarded", "reverted"] as const)(
    "is null for a PR, whatever the server says (%s)",
    (state) => {
      expect(undoneNotice({ kind: "pr", commitState: state })).toBeNull();
    },
  );
});

describe("undoneCounts", () => {
  it("is empty when nothing was undone", () => {
    expect(undoneCounts([commit(), commit({ commitState: "active" })])).toBe("");
    expect(undoneCounts([])).toBe("");
  });

  it("counts discarded and reverted commits apart, in the singular and the plural", () => {
    const one = [commit({ commitState: "discarded" }), commit({ commitState: "reverted" })];
    expect(undoneCounts(one)).toBe("1 deshecho · 1 revertido");
    const many = [
      ...one,
      commit({ commitState: "discarded" }),
      commit({ commitState: "reverted" }),
    ];
    expect(undoneCounts(many)).toBe("2 deshechos · 2 revertidos");
  });

  it("only shows what exists", () => {
    expect(undoneCounts([commit({ commitState: "reverted" })])).toBe("1 revertido");
  });

  it("does not count PRs", () => {
    expect(undoneCounts([{ kind: "pr", commitState: "discarded" }])).toBe("");
  });
});

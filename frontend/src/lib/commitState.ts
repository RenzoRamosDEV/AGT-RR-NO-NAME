import type { Change, CommitState } from "../data/mock";
import { shortSha } from "./url";

/** What the UI says about a commit that is no longer "active". */
export interface UndoneNotice {
  state: Exclude<CommitState, "active">;
  /** Upper-case headline shown in the middle of the row and in the detail banner. */
  label: string;
  /** Smaller line under the headline. */
  subtitle: string;
}

const LABEL: Record<Exclude<CommitState, "active">, string> = {
  discarded: "COMMIT DESHECHO",
  reverted: "COMMIT REVERTIDO",
};

/**
 * The notice for a discarded or reverted commit, or `null` for any other change. A PR is never
 * undone, whatever the server says: the state only means something for commits.
 */
export function undoneNotice(
  change: Pick<Change, "kind" | "commitState" | "revertedBy">,
): UndoneNotice | null {
  if (change.kind !== "commit") return null;
  if (change.commitState === "discarded") {
    return { state: "discarded", label: LABEL.discarded, subtitle: "Ya no está en la rama" };
  }
  if (change.commitState === "reverted") {
    return {
      state: "reverted",
      label: LABEL.reverted,
      subtitle: change.revertedBy
        ? `Revertido por ${shortSha(change.revertedBy.sha)}`
        : "Revertido por otro commit",
    };
  }
  return null;
}

/** "2 deshechos · 1 revertido" for the changes loaded so far; empty when there are none. */
export function undoneCounts(items: readonly Pick<Change, "kind" | "commitState">[]): string {
  const count = (state: CommitState) =>
    items.filter((c) => c.kind === "commit" && c.commitState === state).length;
  const discarded = count("discarded");
  const reverted = count("reverted");
  return [
    discarded > 0 && `${discarded} ${discarded === 1 ? "deshecho" : "deshechos"}`,
    reverted > 0 && `${reverted} ${reverted === 1 ? "revertido" : "revertidos"}`,
  ]
    .filter(Boolean)
    .join(" · ");
}

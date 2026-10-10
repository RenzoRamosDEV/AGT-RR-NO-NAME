import type { Review } from "../data/mock";

export interface PreviousRun {
  run: number;
  reviews: Review[];
}

export interface SplitRuns {
  /** Reviews of the change's current run: the only ones that count for its status and findings. */
  current: Review[];
  /** Reviews of earlier runs (a retry keeps them), newest run first. */
  previous: PreviousRun[];
}

/** A review without `run` belongs to run 1, like the backend's default. */
const runOf = (review: Review) => review.run ?? 1;

/** Splits a change's reviews into the current run and the earlier ones, grouped by run. */
export function splitRuns(reviews: readonly Review[], currentRun: number | undefined): SplitRuns {
  const run = currentRun ?? 1;
  const earlier = new Map<number, Review[]>();
  const current: Review[] = [];
  for (const review of reviews) {
    if (runOf(review) === run) {
      current.push(review);
    } else {
      earlier.set(runOf(review), [...(earlier.get(runOf(review)) ?? []), review]);
    }
  }
  const previous = [...earlier]
    .map(([n, items]) => ({ run: n, reviews: items }))
    .sort((a, b) => b.run - a.run);
  return { current, previous };
}

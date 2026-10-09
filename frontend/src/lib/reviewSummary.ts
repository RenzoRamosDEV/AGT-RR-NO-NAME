import type { Review, ReviewStatus } from "../data/mock";

export interface SummaryItem {
  status: ReviewStatus;
  count: number;
  text: string;
}

const LABELS: Record<ReviewStatus, [string, string]> = {
  completed: ["completada", "completadas"],
  running: ["en curso", "en curso"],
  failed: ["fallida", "fallidas"],
};

const ORDER: ReviewStatus[] = ["completed", "running", "failed"];

/** Counts reviews per status, omitting statuses with no reviews. */
export function summarizeReviews(reviews: Review[]): SummaryItem[] {
  return ORDER.flatMap((status) => {
    const count = reviews.filter((r) => r.status === status).length;
    if (count === 0) return [];
    const [one, many] = LABELS[status];
    return [{ status, count, text: `${count} ${count === 1 ? one : many}` }];
  });
}

import type { Change, Finding, Review } from "../data/mock";

let counter = 0;

export function makeReview(overrides: Partial<Review> = {}): Review {
  counter += 1;
  return { id: `r${counter}`, agent: "claude", status: "completed", ...overrides };
}

export function makeFinding(overrides: Partial<Finding> = {}): Finding {
  return { severity: "low", file: "a.py", line: 1, message: "msg", ...overrides };
}

export function makeChange(overrides: Partial<Change> = {}): Change {
  counter += 1;
  return {
    id: `c${counter}`,
    kind: "commit",
    title: "title",
    author: "renzo",
    sha: "a41f9c2",
    ref: "main",
    url: "",
    diff: "",
    reviews: [],
    ...overrides,
  };
}

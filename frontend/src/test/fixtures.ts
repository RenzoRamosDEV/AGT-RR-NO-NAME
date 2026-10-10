import type { Change, Finding, Review } from "../data/mock";
import { ApiError, type DataSource } from "../lib/api";

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

/** A `DataSource` whose methods can be overridden one by one; the defaults are empty/not found. */
export function makeSource(overrides: Partial<DataSource> = {}): DataSource {
  return {
    projects: async () => [{ slug: "demo", name: "demo" }],
    changes: async () => ({ items: [], nextCursor: null }),
    change: async () => {
      throw new ApiError("no", 404);
    },
    agentStats: async () => [],
    health: async () => ({ status: "ok", dependencies: [], agentNames: ["claude", "codex"] }),
    retry: async () => {
      throw new ApiError("no", 404);
    },
    addProject: async () => {
      throw new ApiError("no", 404);
    },
    removeProject: async () => {
      throw new ApiError("no", 404);
    },
    syncPrs: async () => {
      throw new ApiError("no", 404);
    },
    ...overrides,
  };
}

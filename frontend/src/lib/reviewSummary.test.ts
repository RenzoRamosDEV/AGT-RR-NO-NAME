import { describe, expect, it } from "vitest";
import { summarizeReviews } from "./reviewSummary";

describe("summarizeReviews", () => {
  it("returns nothing for no reviews", () => {
    expect(summarizeReviews([])).toEqual([]);
  });

  it("counts mixed statuses in a stable order and omits empty ones", () => {
    const items = summarizeReviews([
      { agent: "codex", status: "failed" },
      { agent: "claude", status: "completed" },
    ]);
    expect(items.map((i) => i.text)).toEqual(["1 completada", "1 fallida"]);
  });

  it("pluralizes", () => {
    const items = summarizeReviews([
      { agent: "claude", status: "failed" },
      { agent: "codex", status: "failed" },
    ]);
    expect(items).toEqual([{ status: "failed", count: 2, text: "2 fallidas" }]);
  });
});

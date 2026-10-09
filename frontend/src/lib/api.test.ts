import { describe, expect, it, vi } from "vitest";
import { ApiError, createHttpSource } from "./api";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const summary = {
  id: "11111111-1111-1111-1111-111111111111",
  kind: "pr",
  ref: "feat/x",
  head_sha: "9be03d1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  title: "feat: x",
  author: "renzo",
  url: "https://github.com/o/r/pull/1",
  created_at: "2026-10-09T10:00:00Z",
  diff_truncated: true,
};

describe("createHttpSource", () => {
  it("maps projects to slug and name", async () => {
    const fetchMock = vi.fn(async () => jsonResponse([{ id: "p1", slug: "acme/widgets" }]));
    const source = createHttpSource("http://api.test/", fetchMock);
    expect(await source.projects()).toEqual([{ slug: "acme/widgets", name: "acme/widgets" }]);
    expect(fetchMock).toHaveBeenCalledWith("http://api.test/projects", expect.anything());
  });

  it("requests a channel page with kind and an encoded opaque cursor", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ items: [summary], next_cursor: "a+b/c=" }));
    const source = createHttpSource("http://api.test", fetchMock);
    const page = await source.changes("acme/widgets", { kind: "pr", cursor: "x y", limit: 2 });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/projects/acme/widgets/changes?kind=pr&cursor=x+y&limit=2",
      expect.anything(),
    );
    expect(page.nextCursor).toBe("a+b/c=");
    expect(page.items[0]).toMatchObject({
      id: summary.id,
      kind: "pr",
      sha: summary.head_sha,
      ref: "feat/x",
      createdAt: "2026-10-09T10:00:00Z",
      truncated: true,
    });
    expect(page.items[0].reviews).toBeUndefined();
  });

  it("omits the query string without parameters and falls back the title", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({ items: [{ ...summary, title: "" }], next_cursor: null }),
    );
    const source = createHttpSource("http://api.test", fetchMock);
    const page = await source.changes("demo");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/projects/demo/changes",
      expect.anything(),
    );
    expect(page.nextCursor).toBeNull();
    expect(page.items[0].title).toBe("feat/x");
  });

  it("maps a change detail with its reviews and findings", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        ...summary,
        diff: "+a",
        reviews: [
          {
            id: "r1",
            agent: "Codex",
            status: "completed",
            summary: null,
            findings: [{ severity: "high", file: "a.py", line: 3, message: "m" }],
          },
          { id: "r2", agent: "claude", status: "failed", summary: null, findings: [] },
        ],
      }),
    );
    const change = await createHttpSource("http://api.test", fetchMock).change("abc");
    expect(change.diff).toBe("+a");
    expect(change.reviews?.map((r) => [r.id, r.agent, r.status])).toEqual([
      ["r1", "codex", "completed"],
      ["r2", "claude", "failed"],
    ]);
    expect(change.reviews?.[0].summary).toBeUndefined();
    expect(change.reviews?.[0].findings?.[0].line).toBe(3);
  });

  it("raises a not-found ApiError on 404", async () => {
    const source = createHttpSource("http://api.test", async () => jsonResponse({}, 404));
    const error = await source.change("x").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).notFound).toBe(true);
  });

  it("raises an ApiError with the status on 5xx", async () => {
    const source = createHttpSource("http://api.test", async () => jsonResponse({}, 503));
    const error = (await source.projects().catch((e: unknown) => e)) as ApiError;
    expect(error.status).toBe(503);
    expect(error.notFound).toBe(false);
  });

  it("turns a network failure into an ApiError without status", async () => {
    const source = createHttpSource("http://api.test", async () => {
      throw new TypeError("Failed to fetch");
    });
    const error = (await source.projects().catch((e: unknown) => e)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBeNull();
  });

  it("sends repeated status, a trimmed q and omits a blank q", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ items: [], next_cursor: null }));
    const source = createHttpSource("http://api.test", fetchMock);
    await source.changes("demo", { status: ["failed", "partial_failed"], q: "  50% fix " });
    await source.changes("demo", { status: [], q: "   " });
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://api.test/projects/demo/changes?status=failed&status=partial_failed&q=50%25+fix",
      expect.anything(),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://api.test/projects/demo/changes",
      expect.anything(),
    );
  });

  it("maps the aggregate status, run and review metadata", async () => {
    const detail = {
      ...summary,
      run: 2,
      review_status: "partial_failed",
      diff: "",
      reviews: [
        {
          id: "r1",
          agent: "claude",
          status: "failed",
          summary: null,
          findings: [],
          run: 2,
          score: null,
          duration_ms: 1500,
          error: "boom",
        },
      ],
    };
    const source = createHttpSource("http://api.test", async () => jsonResponse(detail));
    const change = await source.change("x");
    expect(change).toMatchObject({ run: 2, reviewStatus: "partial_failed" });
    expect(change.reviews?.[0]).toMatchObject({
      run: 2,
      score: null,
      durationMs: 1500,
      error: "boom",
    });
  });
});

describe("createHttpSource agent stats and health", () => {
  it("maps /stats/agents to the view model, keeping null averages", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse([
        {
          agent: "claude",
          total: 3,
          completed: 2,
          failed: 1,
          avg_duration_ms: 1500,
          avg_score: 7.5,
        },
        {
          agent: "codex",
          total: 0,
          completed: 0,
          failed: 0,
          avg_duration_ms: null,
          avg_score: null,
        },
      ]),
    );
    const stats = await createHttpSource("http://api.test", fetchMock).agentStats();
    expect(fetchMock).toHaveBeenCalledWith("http://api.test/stats/agents", expect.anything());
    expect(stats).toEqual([
      { agent: "claude", total: 3, completed: 2, failed: 1, avgDurationMs: 1500, avgScore: 7.5 },
      { agent: "codex", total: 0, completed: 0, failed: 0, avgDurationMs: null, avgScore: null },
    ]);
  });

  it("maps /health/dependencies to a sorted list with the closed-vocabulary reason", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        status: "degraded",
        dependencies: {
          temporal: { status: "unavailable", latency_ms: 2000, reason: "timeout" },
          postgres: { status: "ok", latency_ms: 4, reason: null },
        },
      }),
    );
    const health = await createHttpSource("http://api.test", fetchMock).health();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/health/dependencies",
      expect.anything(),
    );
    expect(health).toEqual({
      status: "degraded",
      dependencies: [
        { name: "postgres", status: "ok", latencyMs: 4, reason: undefined },
        { name: "temporal", status: "unavailable", latencyMs: 2000, reason: "timeout" },
      ],
    });
  });
});

describe("createHttpSource retry", () => {
  it("POSTs with the ingest token header and returns the new run", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ change_id: "c1", run: 2 }, 202));
    const result = await createHttpSource("http://api.test", fetchMock).retry("c 1", "tok");
    expect(result).toEqual({ changeId: "c1", run: 2 });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/changes/c%201/retry",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-Ingest-Token": "tok" }),
      }),
    );
  });

  it.each([401, 404, 409, 503])("raises an ApiError with status %i", async (status) => {
    const source = createHttpSource("http://api.test", async () => jsonResponse({}, status));
    const error = (await source.retry("c1", "tok").catch((e: unknown) => e)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(status);
  });

  it("turns a network failure into an ApiError without status", async () => {
    const source = createHttpSource("http://api.test", async () => {
      throw new TypeError("Failed to fetch");
    });
    const error = (await source.retry("c1", "tok").catch((e: unknown) => e)) as ApiError;
    expect(error.status).toBeNull();
  });
});

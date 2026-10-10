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

  it("maps a reverted commit's state and the commit that reverts it", async () => {
    const dto = {
      ...summary,
      kind: "commit",
      commit_state: "reverted",
      reverted_by: { id: "22222222-2222-2222-2222-222222222222", head_sha: "d93f0b4cccc" },
    };
    const source = createHttpSource(
      "http://api.test",
      vi.fn(async () => jsonResponse({ items: [dto], next_cursor: null })),
    );
    const [change] = (await source.changes("acme/widgets")).items;
    expect(change.commitState).toBe("reverted");
    expect(change.revertedBy).toEqual({
      id: "22222222-2222-2222-2222-222222222222",
      sha: "d93f0b4cccc",
    });
  });

  it("maps a discarded commit and the detail of a reverted one", async () => {
    const source = createHttpSource(
      "http://api.test",
      vi.fn(async (url: RequestInfo | URL) =>
        String(url).includes("/changes/")
          ? jsonResponse({
              ...summary,
              kind: "commit",
              commit_state: "reverted",
              reverted_by: { id: "r1", head_sha: "abc1234" },
              diff: "",
              reviews: [],
            })
          : jsonResponse({
              items: [{ ...summary, kind: "commit", commit_state: "discarded" }],
              next_cursor: null,
            }),
      ),
    );
    expect((await source.changes("acme/widgets")).items[0].commitState).toBe("discarded");
    const detail = await source.change(summary.id);
    expect(detail.commitState).toBe("reverted");
    expect(detail.revertedBy).toEqual({ id: "r1", sha: "abc1234" });
  });

  it("treats a server that sends no commit state as a normal commit", async () => {
    const source = createHttpSource(
      "http://api.test",
      vi.fn(async () =>
        jsonResponse({ items: [{ ...summary, kind: "commit" }], next_cursor: null }),
      ),
    );
    const [change] = (await source.changes("acme/widgets")).items;
    expect(change.commitState).toBe("active");
    expect(change.revertedBy).toBeUndefined();
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
      ["r1", "Codex", "completed"],
      ["r2", "claude", "failed"],
    ]);
    expect(change.reviews?.[0].summary).toBeUndefined();
    expect(change.reviews?.[0].findings?.[0].line).toBe(3);
  });

  // Regresión: con la API real, `agent_1` y `agent_2` (FakeAgent) salían como «Claude» porque el
  // cliente convertía cualquier agente desconocido en `claude`.
  it("keeps the real name of agents other than claude and codex", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        ...summary,
        diff: "",
        reviews: [{ id: "r1", agent: "agent_1", status: "completed", summary: null, findings: [] }],
      }),
    );
    const change = await createHttpSource("http://api.test", fetchMock).change("abc");
    expect(change.reviews?.[0].agent).toBe("agent_1");
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
        agent_names: ["agent_1", "agent_2"],
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
      agentNames: ["agent_1", "agent_2"],
    });
  });

  it("treats a server that does not report agent_names as having none", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ status: "ok", dependencies: {} }));
    const health = await createHttpSource("http://api.test", fetchMock).health();
    expect(health.agentNames).toEqual([]);
  });

  it("maps the light reviews of the channel listing, keeping the real agent names", async () => {
    // Origin: with the real API «Ver respuestas» was empty and `agent_1` was shown as Claude.
    const brief = { agent: "agent_1", status: "failed", score: null, duration_ms: 7, run: 2 };
    const fetchMock = vi.fn(async () =>
      jsonResponse({ items: [{ ...summary, reviews: [brief] }], next_cursor: null }),
    );
    const page = await createHttpSource("http://api.test", fetchMock).changes("demo");
    expect(page.items[0].reviews).toEqual([
      {
        id: `${summary.id}:agent_1:2`,
        agent: "agent_1",
        status: "failed",
        run: 2,
        score: null,
        durationMs: 7,
        reusedFrom: null,
        partial: true,
      },
    ]);
  });

  it("keeps where a reused review was copied from, in the listing and in the detail", async () => {
    // Origin: a PR identical to a reviewed commit reuses its reviews (`reused_from` = that change).
    const brief = (reused_from?: string | null) => ({
      agent: "claude",
      status: "completed",
      score: 9,
      duration_ms: 5,
      run: 1,
      reused_from,
    });
    const listing = vi.fn(async () =>
      jsonResponse({
        items: [{ ...summary, reviews: [brief("commit-1"), brief(null), brief()] }],
        next_cursor: null,
      }),
    );
    const page = await createHttpSource("http://api.test", listing).changes("demo");
    expect(page.items[0].reviews?.map((r) => r.reusedFrom)).toEqual(["commit-1", null, null]);

    const detail = vi.fn(async () =>
      jsonResponse({
        ...summary,
        diff: "d",
        reviews: [
          { id: "r1", agent: "claude", status: "completed", findings: [], reused_from: "commit-1" },
          { id: "r2", agent: "codex", status: "completed", findings: [] },
        ],
      }),
    );
    const change = await createHttpSource("http://api.test", detail).change("c1");
    expect(change.reviews?.map((r) => r.reusedFrom)).toEqual(["commit-1", null]);
  });

  it("does not treat the full reviews of the detail as partial", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        ...summary,
        diff: "d",
        reviews: [{ id: "r1", agent: "agent_1", status: "completed", summary: "ok", findings: [] }],
      }),
    );
    const change = await createHttpSource("http://api.test", fetchMock).change("c1");
    expect(change.reviews?.[0]?.partial).toBeUndefined();
    expect(change.reviews?.[0]?.summary).toBe("ok");
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

describe("createHttpSource local projects", () => {
  it("maps the path, hooks and GitHub flag of the project list", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse([
        {
          id: "p1",
          slug: "acme/widgets",
          path: "/home/me/widgets",
          hooks_installed: true,
          github: "acme/widgets",
        },
        { id: "p2", slug: "old", path: null, hooks_installed: null, github: null },
      ]),
    );
    expect(await createHttpSource("http://api.test", fetchMock).projects()).toEqual([
      {
        slug: "acme/widgets",
        name: "acme/widgets",
        path: "/home/me/widgets",
        hooksInstalled: true,
        github: true,
      },
      { slug: "old", name: "old" },
    ]);
  });

  it("POSTs the path as JSON with the token and maps the created project", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse(
        { id: "p1", slug: "acme/widgets", path: "/r", hooks_installed: true, github: false },
        201,
      ),
    );
    const project = await createHttpSource("http://api.test", fetchMock).addProject("/r", "tok");
    expect(project).toEqual({
      slug: "acme/widgets",
      name: "acme/widgets",
      path: "/r",
      hooksInstalled: true,
      github: false,
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/projects",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ path: "/r" }),
        headers: expect.objectContaining({
          "X-Ingest-Token": "tok",
          "Content-Type": "application/json",
        }),
      }),
    );
  });

  it.each([401, 404, 409, 422])("raises an ApiError with status %i on add", async (status) => {
    const source = createHttpSource("http://api.test", async () => jsonResponse({}, status));
    const error = (await source.addProject("/r", "t").catch((e: unknown) => e)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(status);
  });

  it("DELETEs an owner/repo slug as a path and accepts the empty 204 body", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 204 }));
    await expect(
      createHttpSource("http://api.test", fetchMock).removeProject("acme/wid gets", "tok"),
    ).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/projects/acme/wid%20gets",
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining({ "X-Ingest-Token": "tok" }),
      }),
    );
  });

  it("POSTs sync-prs and returns the counters", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ synced: 3, created: 1 }));
    const result = await createHttpSource("http://api.test", fetchMock).syncPrs(
      "acme/widgets",
      "t",
    );
    expect(result).toEqual({ synced: 3, created: 1 });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/projects/acme/widgets/sync-prs",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("uses the textual `detail` of an error as its message", async () => {
    const source = createHttpSource("http://api.test", async () =>
      jsonResponse({ detail: "gh no está instalado" }, 503),
    );
    const error = (await source.syncPrs("a/b", "t").catch((e: unknown) => e)) as ApiError;
    expect(error.status).toBe(503);
    expect(error.message).toBe("gh no está instalado");
  });

  it("keeps the generic message when `detail` is a validation list or the body is not JSON", async () => {
    const list = createHttpSource("http://api.test", async () =>
      jsonResponse({ detail: [{ msg: "bad", loc: ["body"] }] }, 422),
    );
    const listError = (await list.addProject("/r", "t").catch((e: unknown) => e)) as ApiError;
    expect(listError.message).toBe("El servidor respondió 422.");

    const html = createHttpSource(
      "http://api.test",
      async () => new Response("<html>", { status: 502 }),
    );
    const htmlError = (await html.addProject("/r", "t").catch((e: unknown) => e)) as ApiError;
    expect(htmlError.message).toBe("El servidor respondió 502.");
  });
});

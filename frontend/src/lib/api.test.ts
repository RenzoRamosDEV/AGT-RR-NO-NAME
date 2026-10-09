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
});

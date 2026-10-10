import { describe, expect, it } from "vitest";
import type { ApiError } from "../lib/api";
import { createMockSource } from "./source";

describe("createMockSource", () => {
  it("derives the aggregate review status", async () => {
    const page = await createMockSource().changes("duelo");
    expect(page.items.map((c) => [c.id, c.reviewStatus])).toEqual([
      ["c1", "running"],
      ["c3", "completed"],
      ["c4", "completed"],
      ["c5", "completed"],
      ["c2", "partial_failed"],
    ]);
  });

  it("filters by kind, status and q like the server", async () => {
    const source = createMockSource();
    const ids = async (query: Parameters<typeof source.changes>[1]) =>
      (await source.changes("duelo", query)).items.map((c) => c.id);
    expect(await ids({ kind: "pr" })).toEqual(["c2"]);
    expect(await ids({ status: ["pending", "running"] })).toEqual(["c1"]);
    expect(await ids({ status: ["failed", "partial_failed"] })).toEqual(["c2"]);
    expect(await ids({ status: ["completed"] })).toEqual(["c3", "c4", "c5"]);
    expect(await ids({ q: "  TOKEN " })).toEqual(["c1"]);
    expect(await ids({ q: "feat/ingest" })).toEqual(["c2"]);
    expect(await ids({ status: ["failed", "partial_failed"], q: "token" })).toEqual([]);
  });

  it("paginates with an offset cursor", async () => {
    const source = createMockSource();
    const first = await source.changes("duelo", { limit: 1 });
    expect(first.items.map((c) => c.id)).toEqual(["c1"]);
    const second = await source.changes("duelo", { limit: 1, cursor: first.nextCursor });
    expect(second.items.map((c) => c.id)).toEqual(["c3"]);
    expect(second.nextCursor).not.toBeNull();
    const last = await source.changes("duelo", { limit: 3, cursor: second.nextCursor });
    expect(last.items.map((c) => c.id)).toEqual(["c4", "c5", "c2"]);
    expect(last.nextCursor).toBeNull();
  });

  it("reports a discarded and a reverted commit, and the commit that reverts it", async () => {
    const source = createMockSource();
    expect(await source.change("c3")).toMatchObject({ commitState: "discarded" });
    expect(await source.change("c4")).toMatchObject({
      commitState: "reverted",
      revertedBy: { id: "c5", sha: "d93f0b4" },
    });
    expect((await source.change("c5")).commitState).toBe("active");
  });

  it("restarts a failed change on retry without touching other sources", async () => {
    const source = createMockSource();
    expect(await source.retry("c2", "tok")).toEqual({ changeId: "c2", run: 2 });
    const after = await source.change("c2");
    expect(after).toMatchObject({ run: 2, reviewStatus: "pending", reviews: [] });
    expect((await createMockSource().change("c2")).reviewStatus).toBe("partial_failed");
  });

  it("rejects a retry without token, unknown or not retryable", async () => {
    const source = createMockSource();
    const status = async (id: string, token: string) =>
      ((await source.retry(id, token).catch((e: unknown) => e)) as ApiError).status;
    expect(await status("c2", "  ")).toBe(401);
    expect(await status("nope", "tok")).toBe(404);
    expect(await status("c1", "tok")).toBe(409);
  });
});

describe("createMockSource local projects", () => {
  const status = async (promise: Promise<unknown>) =>
    ((await promise.catch((e: unknown) => e)) as ApiError).status;

  it("adds a project with the same error rules as the API", async () => {
    const source = createMockSource();
    expect(await status(source.addProject("/home/me/foo/bar", " "))).toBe(401);
    expect(await status(source.addProject("repo/relativo", "tok"))).toBe(422);
    expect(await status(source.addProject("/", "tok"))).toBe(422);

    const added = await source.addProject("/home/me/foo/bar", "tok");
    expect(added).toMatchObject({
      slug: "foo/bar",
      path: "/home/me/foo/bar",
      hooksInstalled: true,
    });
    expect((await source.projects()).map((p) => p.slug)).toContain("foo/bar");
    expect(await status(source.addProject("/other/foo/bar", "tok"))).toBe(409);
    expect(await source.changes("foo/bar")).toEqual({ items: [], nextCursor: null });
  });

  it("keeps projects per source", async () => {
    const source = createMockSource();
    await source.addProject("/x/foo/bar", "tok");
    expect((await createMockSource().projects()).map((p) => p.slug)).not.toContain("foo/bar");
  });

  it("removes added and sample projects, and then they are gone", async () => {
    const source = createMockSource();
    await source.addProject("/x/foo/bar", "tok");
    expect(await status(source.removeProject("foo/bar", ""))).toBe(401);
    await source.removeProject("foo/bar", "tok");
    for (const { slug } of await source.projects()) await source.removeProject(slug, "tok");
    expect(await source.projects()).toEqual([]);
    expect(await status(source.removeProject("duelo", "tok"))).toBe(404);
    expect(await status(source.changes("duelo"))).toBe(404);
  });

  it("answers 503 when syncing a project that is not on GitHub", async () => {
    const source = createMockSource();
    expect(await status(source.syncPrs("duelo", ""))).toBe(401);
    expect(await status(source.syncPrs("nope", "tok"))).toBe(404);
    expect(await status(source.syncPrs("duelo", "tok"))).toBe(503);
  });
});

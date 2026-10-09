import { describe, expect, it } from "vitest";
import type { ApiError } from "../lib/api";
import { createMockSource } from "./source";

describe("createMockSource", () => {
  it("derives the aggregate review status", async () => {
    const page = await createMockSource().changes("duelo");
    expect(page.items.map((c) => [c.id, c.reviewStatus])).toEqual([
      ["c1", "running"],
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
    expect(await ids({ status: ["completed"] })).toEqual([]);
    expect(await ids({ q: "  TOKEN " })).toEqual(["c1"]);
    expect(await ids({ q: "feat/ingest" })).toEqual(["c2"]);
    expect(await ids({ status: ["failed", "partial_failed"], q: "token" })).toEqual([]);
  });

  it("paginates with an offset cursor", async () => {
    const source = createMockSource();
    const first = await source.changes("duelo", { limit: 1 });
    expect(first.items.map((c) => c.id)).toEqual(["c1"]);
    const second = await source.changes("duelo", { limit: 1, cursor: first.nextCursor });
    expect(second.items.map((c) => c.id)).toEqual(["c2"]);
    expect(second.nextCursor).toBeNull();
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

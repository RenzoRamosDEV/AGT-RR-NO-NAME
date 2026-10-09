import { describe, expect, it } from "vitest";
import { changePath, parseProjectPath, projectPath } from "./projectPath";

describe("projectPath", () => {
  it("keeps the slash of owner/repo and encodes each segment", () => {
    expect(projectPath("acme/widgets")).toBe("/p/acme/widgets");
    expect(projectPath("duelo")).toBe("/p/duelo");
    expect(projectPath("a b/c?d")).toBe("/p/a%20b/c%3Fd");
  });

  it("builds the change path", () => {
    expect(changePath("acme/widgets", "c 1")).toBe("/p/acme/widgets/changes/c%201");
  });
});

describe("parseProjectPath", () => {
  it("reads a channel with one or several segments", () => {
    expect(parseProjectPath("duelo")).toEqual({ kind: "channel", slug: "duelo" });
    expect(parseProjectPath("acme/widgets")).toEqual({ kind: "channel", slug: "acme/widgets" });
  });

  it("reads a change detail", () => {
    expect(parseProjectPath("acme/widgets/changes/c1")).toEqual({
      kind: "change",
      slug: "acme/widgets",
      id: "c1",
    });
    expect(parseProjectPath("duelo/changes/c1")).toEqual({
      kind: "change",
      slug: "duelo",
      id: "c1",
    });
  });

  it("treats a project named 'changes' as a channel", () => {
    expect(parseProjectPath("changes")).toEqual({ kind: "channel", slug: "changes" });
    expect(parseProjectPath("x/changes")).toEqual({ kind: "channel", slug: "x/changes" });
  });

  it("returns none for an empty path", () => {
    expect(parseProjectPath(undefined)).toEqual({ kind: "none" });
    expect(parseProjectPath("")).toEqual({ kind: "none" });
    expect(parseProjectPath("/")).toEqual({ kind: "none" });
  });

  it("round-trips what changePath builds", () => {
    const route = parseProjectPath(changePath("acme/widgets", "c1").slice("/p/".length));
    expect(route).toEqual({ kind: "change", slug: "acme/widgets", id: "c1" });
  });
});

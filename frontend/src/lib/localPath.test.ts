import { describe, expect, it } from "vitest";
import { isAbsolutePath, slugFromPath } from "./localPath";

describe("isAbsolutePath", () => {
  it.each(["/home/me/repo", "  /srv/app ", "C:\\work\\repo", "d:/work/repo"])(
    "accepts %s",
    (path) => expect(isAbsolutePath(path)).toBe(true),
  );

  it.each(["", "repo", "./repo", "../repo", "~/repo", "C:repo", "home/me/repo"])(
    "rejects %j",
    (path) => expect(isAbsolutePath(path)).toBe(false),
  );
});

describe("slugFromPath", () => {
  it("uses the last two segments", () => {
    expect(slugFromPath("/home/me/acme/widgets")).toBe("acme/widgets");
    expect(slugFromPath("/home/me/acme/widgets/")).toBe("acme/widgets");
    expect(slugFromPath("C:\\work\\acme\\widgets")).toBe("acme/widgets");
  });

  it("falls back to a single segment and to empty for a root", () => {
    expect(slugFromPath("/repo")).toBe("repo");
    expect(slugFromPath("/")).toBe("");
    expect(slugFromPath("C:\\")).toBe("");
  });
});

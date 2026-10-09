import { describe, expect, it } from "vitest";
import { safeHttpUrl, shortSha } from "./url";

describe("safeHttpUrl", () => {
  it("accepts http and https", () => {
    expect(safeHttpUrl("https://github.com/o/r/pull/1")).toBe("https://github.com/o/r/pull/1");
    expect(safeHttpUrl("http://localhost:3000/x")).toBe("http://localhost:3000/x");
  });

  it("rejects other schemes, relative and empty values", () => {
    for (const bad of ["javascript:alert(1)", "data:text/html,x", "ftp://x/y", "/relative", ""]) {
      expect(safeHttpUrl(bad)).toBeNull();
    }
  });
});

describe("shortSha", () => {
  it("abbreviates to seven characters and keeps short values", () => {
    expect(shortSha("9be03d1aaaaaaaaaaaa")).toBe("9be03d1");
    expect(shortSha("abc")).toBe("abc");
  });
});

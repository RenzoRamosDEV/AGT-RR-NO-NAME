import { describe, expect, it } from "vitest";
import { relativeTime } from "./relativeTime";

const NOW = new Date("2026-10-09T12:00:00Z");
const ago = (ms: number) => new Date(NOW.getTime() - ms).toISOString();

describe("relativeTime", () => {
  it.each([
    [0, "hace un momento"],
    [59_999, "hace un momento"],
    [60_000, "hace 1 min"],
    [12 * 60_000, "hace 12 min"],
    [59 * 60_000 + 59_999, "hace 59 min"],
    [60 * 60_000, "hace 1 h"],
    [23 * 3_600_000, "hace 23 h"],
    [24 * 3_600_000, "hace 1 día"],
    [30 * 86_400_000, "hace 30 días"],
  ])("%d ms ago -> %s", (ms, expected) => {
    expect(relativeTime(ago(ms), NOW)).toBe(expected);
  });

  it("falls back to the absolute date after 30 days", () => {
    expect(relativeTime(ago(31 * 86_400_000), NOW)).toBe(
      new Date(ago(31 * 86_400_000)).toLocaleDateString("es-ES"),
    );
  });

  it("treats a future date as just now", () => {
    expect(relativeTime(new Date(NOW.getTime() + 5 * 60_000).toISOString(), NOW)).toBe(
      "hace un momento",
    );
  });

  it("returns null for an invalid date", () => {
    expect(relativeTime("nope", NOW)).toBeNull();
  });
});

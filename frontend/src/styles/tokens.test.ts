import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { contrastRatio } from "../lib/contrast";

const read = (rel: string) => readFileSync(new URL(rel, import.meta.url), "utf8");
const tokens = read("./tokens.css");
const index = read("../index.css");

function token(name: string): string {
  const m = tokens.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!m) throw new Error(`token --${name} not found`);
  return m[1];
}

describe("black theme", () => {
  it("pins a dark color scheme and black background regardless of system preference", () => {
    expect(tokens).toContain("color-scheme: dark");
    expect(token("bg")).toBe("#000000");
    expect(`${tokens}${index}`).not.toMatch(/prefers-color-scheme/);
    expect(index).not.toMatch(/color-scheme:\s*light/);
  });

  it.each(["bg", "surface", "surface-2"])("muted text has AA contrast on --%s", (surface) => {
    expect(contrastRatio(token("fg-muted"), token(surface))).toBeGreaterThanOrEqual(4.5);
  });

  it.each(["fg", "success", "danger", "warning"])("--%s text has AA contrast on surfaces", (fg) => {
    for (const s of ["bg", "surface", "surface-2"]) {
      expect(contrastRatio(token(fg), token(s))).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("primary button text has AA contrast on the accent", () => {
    expect(contrastRatio(token("accent-fg"), token("accent"))).toBeGreaterThanOrEqual(4.5);
  });
});

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { contrastRatio } from "../lib/contrast";

const read = (rel: string) => readFileSync(new URL(rel, import.meta.url), "utf8");
const tokens = read("./tokens.css");
const index = read("../index.css");
const html = read("../../index.html");

/** The declarations inside the block that starts with `selector {`. */
function block(selector: string): string {
  const start = tokens.indexOf(`${selector} {`);
  if (start < 0) throw new Error(`block ${selector} not found`);
  return tokens.slice(start, tokens.indexOf("\n}", start));
}

const THEMES = {
  dark: block(":root"),
  light: block(':root[data-theme="light"]'),
} as const;

function token(theme: keyof typeof THEMES, name: string): string {
  const m = THEMES[theme].match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!m) throw new Error(`token --${name} not found in the ${theme} theme`);
  return m[1];
}

const SURFACES = ["bg", "bg-subtle", "bg-inset", "bg-hover"];

describe("themes", () => {
  it("is dark by default and light under data-theme, with a no-script system fallback", () => {
    expect(THEMES.dark).toContain("color-scheme: dark");
    expect(THEMES.light).toContain("color-scheme: light");
    expect(tokens).toMatch(
      /@media \(prefers-color-scheme: light\)\s*{\s*:root:not\(\[data-theme\]\)/,
    );
  });

  it("sets the theme before first paint, from the stored preference or the system", () => {
    expect(html).toContain('localStorage.getItem("duelo-theme")');
    expect(html).toContain('setAttribute("data-theme"');
    expect(html).toContain("prefers-color-scheme: light");
  });

  it("uses no loose colors: components read the tokens", () => {
    const withoutRgba = index.replace(/rgba\([^)]*\)/g, "");
    // Hex colors belong to the tokens, except the avatar's white text and color-mix's black.
    const loose = withoutRgba.match(/#[0-9a-fA-F]{3,8}\b/g) ?? [];
    expect(loose.filter((c) => !["#ffffff", "#000"].includes(c.toLowerCase()))).toEqual([]);
  });
});

describe.each(["dark", "light"] as const)("%s theme contrast (WCAG AA)", (theme) => {
  it.each(SURFACES)("muted text has AA contrast on --%s", (surface) => {
    expect(contrastRatio(token(theme, "fg-muted"), token(theme, surface))).toBeGreaterThanOrEqual(
      4.5,
    );
  });

  it.each(["fg", "accent", "success", "danger", "warning", "done"])(
    "--%s text has AA contrast on every surface",
    (fg) => {
      for (const surface of ["bg", "bg-subtle", "bg-inset"]) {
        expect(contrastRatio(token(theme, fg), token(theme, surface))).toBeGreaterThanOrEqual(4.5);
      }
    },
  );

  it.each([
    ["accent", "accent-bg"],
    ["success", "success-bg"],
    ["danger", "danger-bg"],
    ["warning", "warning-bg"],
    ["done", "done-bg"],
  ])("--%s text has AA contrast on its tinted background --%s", (fg, bg) => {
    expect(contrastRatio(token(theme, fg), token(theme, bg))).toBeGreaterThanOrEqual(4.5);
  });

  it("the selected sidebar item (on-emphasis on accent-emphasis) is readable", () => {
    expect(
      contrastRatio(token(theme, "on-emphasis"), token(theme, "accent-emphasis")),
    ).toBeGreaterThanOrEqual(4.5);
  });

  it("the green button text has AA contrast on its background, normal and hovered", () => {
    expect(
      contrastRatio(token(theme, "primary-fg"), token(theme, "primary-bg")),
    ).toBeGreaterThanOrEqual(4.5);
    expect(
      contrastRatio(token(theme, "primary-fg"), token(theme, "primary-hover")),
    ).toBeGreaterThanOrEqual(4.5);
  });

  it("diff text stays readable over the added, deleted and hunk backgrounds", () => {
    for (const bg of ["diff-add-bg", "diff-del-bg", "diff-hunk-bg"]) {
      expect(contrastRatio(token(theme, "fg"), token(theme, bg))).toBeGreaterThanOrEqual(4.5);
      expect(contrastRatio(token(theme, "fg-muted"), token(theme, bg))).toBeGreaterThanOrEqual(4.5);
    }
  });
});

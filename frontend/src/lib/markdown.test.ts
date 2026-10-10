import { describe, expect, it } from "vitest";
import { type Inline, MAX_MARKDOWN_CHARS, parseInline, parseMarkdown } from "./markdown";

const text = (value: string): Inline => ({ type: "text", value });

describe("parseInline", () => {
  it("keeps plain text and turns line breaks into br", () => {
    expect(parseInline("uno\ndos")).toEqual([text("uno"), { type: "br" }, text("dos")]);
  });

  it("renders inline code without the backticks and does not format inside it", () => {
    expect(parseInline("mira `**README.md**` ya")).toEqual([
      text("mira "),
      { type: "code", value: "**README.md**" },
      text(" ya"),
    ]);
  });

  it("supports code with double backticks around a single one", () => {
    expect(parseInline("``a`b``")).toEqual([{ type: "code", value: "a`b" }]);
  });

  it("leaves an unclosed backtick as text", () => {
    expect(parseInline("sobra ` aquí")).toEqual([text("sobra ` aquí")]);
  });

  it("renders bold and italics", () => {
    expect(parseInline("**fuerte** y *suave*")).toEqual([
      { type: "strong", children: [text("fuerte")] },
      text(" y "),
      { type: "em", children: [text("suave")] },
    ]);
  });

  it("does not turn snake_case or a lone star into emphasis", () => {
    expect(parseInline("usa agent_name_x y 2 * 3 * 4")).toEqual([
      text("usa agent_name_x y 2 * 3 * 4"),
    ]);
  });

  it("renders emphasis with underscores only at word boundaries", () => {
    expect(parseInline("_hola_ __mundo__")).toEqual([
      { type: "em", children: [text("hola")] },
      text(" "),
      { type: "strong", children: [text("mundo")] },
    ]);
  });

  it("nests formatting inside bold", () => {
    expect(parseInline("**ver `x`**")).toEqual([
      { type: "strong", children: [text("ver "), { type: "code", value: "x" }] },
    ]);
  });

  it("renders http and https links, markdown or bare", () => {
    expect(parseInline("[docs](https://example.com/a?b=1) y https://example.org/x.")).toEqual([
      { type: "link", href: "https://example.com/a?b=1", children: [text("docs")] },
      text(" y "),
      { type: "link", href: "https://example.org/x", children: [text("https://example.org/x")] },
      text("."),
    ]);
  });

  it("honours backslash escapes", () => {
    expect(parseInline("\\*no\\* \\`ni esto\\`")).toEqual([text("*no* `ni esto`")]);
  });

  it("does not format across the cap of nesting", () => {
    const deep = `${"*a ".repeat(2)}`;
    expect(() => parseInline(deep)).not.toThrow();
  });
});

describe("parseInline with hostile input", () => {
  const hasLink = (nodes: Inline[]): boolean =>
    nodes.some(
      (n) =>
        n.type === "link" || ("children" in n && hasLink((n as { children: Inline[] }).children)),
    );

  it("never produces a link for javascript:, data: or file: URLs", () => {
    for (const bad of [
      "[x](javascript:alert(1))",
      "[x](JaVaScRiPt:alert(1))",
      "[x](data:text/html;base64,PHNjcmlwdD4=)",
      "[x](file:///etc/passwd)",
      "[x](vbscript:msgbox(1))",
      "[x](//evil.example/x)",
      "[x](/relativa)",
    ]) {
      expect(hasLink(parseInline(bad))).toBe(false);
    }
  });

  it("keeps HTML as literal text: the tree has no element type for it", () => {
    const nodes = parseInline("<script>alert(1)</script><img src=x onerror=alert(1)>");
    expect(nodes).toEqual([text("<script>alert(1)</script><img src=x onerror=alert(1)>")]);
  });

  it("does not create images: the marker and the rest stay as text", () => {
    const nodes = parseInline("![logo](https://example.com/a.png)");
    expect(nodes.every((n) => n.type === "text" || n.type === "link")).toBe(true);
    expect(nodes.some((n) => n.type === "text" && n.value.startsWith("!["))).toBe(true);
  });

  it("does not make a markdown link out of a URL with spaces; only the bare http part is linked", () => {
    const nodes = parseInline("[x](https://example.com/a b)");
    const links = nodes.filter((n) => n.type === "link");
    expect(links.every((n) => n.type === "link" && n.href.startsWith("https://"))).toBe(true);
    expect(
      links.some(
        (n) => n.type === "link" && n.children[0]?.type === "text" && n.children[0].value === "x",
      ),
    ).toBe(false);
  });

  it("stays fast on delimiters that never close", () => {
    const started = performance.now();
    parseInline("**a ".repeat(4000));
    parseInline("`a ".repeat(4000));
    parseInline("[a](".repeat(3000));
    parseInline("_a ".repeat(4000));
    expect(performance.now() - started).toBeLessThan(2000);
  });

  it("shows oversized input as plain text", () => {
    const huge = `**${"a".repeat(MAX_MARKDOWN_CHARS)}**`;
    expect(parseInline(huge)).toEqual([text(huge)]);
  });
});

describe("parseMarkdown", () => {
  it("splits paragraphs on blank lines and keeps single line breaks", () => {
    expect(parseMarkdown("uno\ndos\n\ntres")).toEqual([
      { type: "paragraph", children: [text("uno"), { type: "br" }, text("dos")] },
      { type: "paragraph", children: [text("tres")] },
    ]);
  });

  it("normalizes CRLF", () => {
    expect(parseMarkdown("a\r\n\r\nb")).toHaveLength(2);
  });

  it("parses bullet and numbered lists", () => {
    expect(parseMarkdown("- uno\n- dos\n\n1. primero\n2) segundo")).toEqual([
      { type: "list", ordered: false, items: [[text("uno")], [text("dos")]] },
      { type: "list", ordered: true, items: [[text("primero")], [text("segundo")]] },
    ]);
  });

  it("keeps a list going across a blank line and folds indented continuation lines", () => {
    expect(parseMarkdown("- a\n  sigue\n\n- b")).toEqual([
      {
        type: "list",
        ordered: false,
        items: [[text("a"), { type: "br" }, text("sigue")], [text("b")]],
      },
    ]);
  });

  it("does not take **bold** at the start of a line for a list", () => {
    expect(parseMarkdown("**Ojo**: algo")).toEqual([
      {
        type: "paragraph",
        children: [{ type: "strong", children: [text("Ojo")] }, text(": algo")],
      },
    ]);
  });

  it("parses fenced code blocks and ignores the language", () => {
    expect(parseMarkdown("antes\n```ts\nconst a = `x`;\n\nlet b;\n```\ndespués")).toEqual([
      { type: "paragraph", children: [text("antes")] },
      { type: "code", value: "const a = `x`;\n\nlet b;" },
      { type: "paragraph", children: [text("después")] },
    ]);
  });

  it("runs an unclosed fence to the end", () => {
    expect(parseMarkdown("```\ncódigo\nmás")).toEqual([{ type: "code", value: "código\nmás" }]);
  });

  it("does not format the inside of a code block", () => {
    expect(parseMarkdown("```\n**x** [a](https://e.com) <b>\n```")).toEqual([
      { type: "code", value: "**x** [a](https://e.com) <b>" },
    ]);
  });

  it("shows headings as a bold line", () => {
    expect(parseMarkdown("## Resumen\ntexto")).toEqual([
      { type: "paragraph", children: [{ type: "strong", children: [text("Resumen")] }] },
      { type: "paragraph", children: [text("texto")] },
    ]);
  });

  it("returns nothing for empty input", () => {
    expect(parseMarkdown("")).toEqual([]);
    expect(parseMarkdown("\n \n")).toEqual([]);
  });

  it("shows oversized input as one plain paragraph", () => {
    const huge = `# x\n${"a".repeat(MAX_MARKDOWN_CHARS)}`;
    const [block] = parseMarkdown(huge);
    expect(block?.type).toBe("paragraph");
    expect(parseMarkdown(huge)).toHaveLength(1);
  });
});

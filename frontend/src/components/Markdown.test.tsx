import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Markdown } from "./Markdown";

const html = (text: string) => render(<Markdown text={text} />).container;

describe("Markdown", () => {
  it("renders `code` as a code element without the backticks", () => {
    const container = html("Cambia `README.md` ya");
    const code = container.querySelector("code.md-code");
    expect(code).toHaveTextContent("README.md");
    expect(container).not.toHaveTextContent("`");
  });

  it("renders paragraphs, line breaks, bold and italics", () => {
    const container = html("**Ojo**: *sí*\nsegunda línea\n\notro párrafo");
    expect(container.querySelectorAll("p")).toHaveLength(2);
    expect(container.querySelector("strong")).toHaveTextContent("Ojo");
    expect(container.querySelector("em")).toHaveTextContent("sí");
    expect(container.querySelectorAll("br")).toHaveLength(1);
  });

  it("renders bullet and numbered lists", () => {
    const container = html("- uno\n- dos\n\n1. a\n2. b");
    expect(container.querySelectorAll("ul > li")).toHaveLength(2);
    expect(container.querySelectorAll("ol > li")).toHaveLength(2);
  });

  it("renders fenced code as a block that keeps its text", () => {
    const container = html("```ts\nconst x = `a`;\n```");
    expect(container.querySelector("pre.md-pre code")?.textContent).toBe("const x = `a`;");
  });

  it("opens http and https links in a new tab without leaking the opener", () => {
    const container = html("[docs](https://example.com/a) y http://example.org");
    const links = container.querySelectorAll("a");
    expect(links).toHaveLength(2);
    for (const link of links) {
      expect(link).toHaveAttribute("target", "_blank");
      expect(link.getAttribute("rel")).toContain("noopener");
      expect(link.getAttribute("rel")).toContain("noreferrer");
    }
  });

  it("renders nothing for empty text", () => {
    expect(html("   ").innerHTML).toBe("");
  });
});

describe("Markdown with hostile text", () => {
  it("shows HTML as text and creates no script, image, iframe or handler", () => {
    const container = html(
      "<script>alert(1)</script><img src=x onerror=alert(1)><iframe src=//e></iframe><b onclick=x()>b</b>",
    );
    expect(container.querySelector("script, img, iframe, b")).toBeNull();
    // The markup is escaped in the DOM, so the serialized text holds `&lt;` and never a real tag.
    expect(container.innerHTML).not.toMatch(/<(script|img|iframe)/i);
    expect(container).toHaveTextContent("<script>alert(1)</script>");
    expect(container).toHaveTextContent("<img src=x onerror=alert(1)>");
  });

  it("never creates a link for javascript:, data: or file: URLs", () => {
    const container = html(
      "[a](javascript:alert(1)) [b](data:text/html;base64,AAAA) [c](file:///etc/passwd) javascript:alert(2)",
    );
    expect(container.querySelector("a")).toBeNull();
    expect(container).toHaveTextContent("[a](javascript:alert(1))");
  });

  it("never creates an image element from image syntax", () => {
    const container = html("![x](https://example.com/a.png) ![y](javascript:alert(1))");
    expect(container.querySelector("img")).toBeNull();
  });

  it("keeps a link's own text free of markup", () => {
    const container = html("[<img src=x onerror=alert(1)>](https://example.com)");
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("a")).toHaveTextContent("<img src=x onerror=alert(1)>");
  });

  it("does not interpret formatting inside a code block", () => {
    const container = html("```\n**x** <b>y</b> [a](https://e.com)\n```");
    expect(container.querySelector("strong, b, a")).toBeNull();
    expect(container.querySelector("code")?.textContent).toBe("**x** <b>y</b> [a](https://e.com)");
  });
});

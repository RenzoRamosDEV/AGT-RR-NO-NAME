import { safeHttpUrl } from "./url";

/**
 * A small, safe subset of Markdown for the text agents write (summaries, finding messages).
 *
 * The output is a tree that React renders as elements, so any text is escaped by React: nothing
 * here can create HTML. Only `http` and `https` links exist, images do not, and the scan is linear
 * (`indexOf`, no backtracking regular expressions) with caps on size and nesting so a hostile
 * input cannot freeze the page.
 */
export type Inline =
  | { type: "text"; value: string }
  | { type: "code"; value: string }
  | { type: "strong"; children: Inline[] }
  | { type: "em"; children: Inline[] }
  | { type: "link"; href: string; children: Inline[] }
  | { type: "br" };

export type Block =
  | { type: "paragraph"; children: Inline[] }
  | { type: "list"; ordered: boolean; items: Inline[][] }
  | { type: "code"; value: string };

/** Above this the text is shown as plain lines: parsing it is not worth the risk. */
export const MAX_MARKDOWN_CHARS = 20_000;
const MAX_DEPTH = 4;
const ESCAPABLE = "\\`*_[]()#+-.!<>~|";

const isAlnum = (char: string | undefined): boolean => !!char && /[\p{L}\p{N}]/u.test(char);
const isSpace = (char: string | undefined): boolean => char === undefined || /\s/.test(char);

/** Plain text with its line breaks, used for oversized input and as the fallback. */
function plainInlines(text: string): Inline[] {
  const out: Inline[] = [];
  text.split("\n").forEach((line, index) => {
    if (index > 0) out.push({ type: "br" });
    if (line) out.push({ type: "text", value: line });
  });
  return out;
}

/** The index of the closing run of exactly `length` backticks, or -1. */
function closingBackticks(text: string, from: number, length: number): number {
  const delimiter = "`".repeat(length);
  let at = text.indexOf(delimiter, from);
  while (at !== -1) {
    const before = text[at - 1];
    const after = text[at + length];
    if (before !== "`" && after !== "`") return at;
    // A longer run: skip it whole so "``a```" does not close early.
    let end = at;
    while (text[end] === "`") end += 1;
    at = text.indexOf(delimiter, end);
  }
  return -1;
}

function parseInlineAt(text: string, depth: number): Inline[] {
  const out: Inline[] = [];
  let buffer = "";
  // A delimiter that already failed to find its closing one cannot succeed later in this text.
  const noClose = new Set<string>();
  const flush = () => {
    if (buffer) out.push({ type: "text", value: buffer });
    buffer = "";
  };
  let i = 0;
  while (i < text.length) {
    const char = text[i] as string;

    if (char === "\n") {
      flush();
      out.push({ type: "br" });
      i += 1;
      continue;
    }

    if (char === "\\" && i + 1 < text.length && ESCAPABLE.includes(text[i + 1] as string)) {
      buffer += text[i + 1];
      i += 2;
      continue;
    }

    if (char === "`") {
      let length = 0;
      while (text[i + length] === "`") length += 1;
      const close = closingBackticks(text, i + length, length);
      if (close !== -1) {
        let value = text.slice(i + length, close);
        if (value.length > 1 && value.startsWith(" ") && value.endsWith(" ") && value.trim()) {
          value = value.slice(1, -1);
        }
        if (value) {
          flush();
          out.push({ type: "code", value });
          i = close + length;
          continue;
        }
      }
      buffer += "`".repeat(length);
      i += length;
      continue;
    }

    // Images do not exist: the marker and the rest stay as text (the link below never starts).
    if (char === "!" && text[i + 1] === "[") {
      buffer += "![";
      i += 2;
      continue;
    }

    if (depth < MAX_DEPTH) {
      if (char === "[") {
        const closeLabel = text.indexOf("]", i + 1);
        if (closeLabel !== -1 && text[closeLabel + 1] === "(") {
          const closeUrl = text.indexOf(")", closeLabel + 2);
          const label = text.slice(i + 1, closeLabel);
          const href = closeUrl === -1 ? null : safeHttpUrl(text.slice(closeLabel + 2, closeUrl));
          if (
            href &&
            label.trim() &&
            !label.includes("\n") &&
            !/\s/.test(text.slice(closeLabel + 2, closeUrl))
          ) {
            flush();
            out.push({ type: "link", href, children: parseInlineAt(label, depth + 1) });
            i = closeUrl + 1;
            continue;
          }
        }
      }

      if (char === "*" || char === "_") {
        const double = text[i + 1] === char;
        const delimiter = double ? char + char : char;
        const key = delimiter;
        // `_` only opens at a word boundary, so snake_case_names stay as they are.
        const opensHere = char === "*" || !isAlnum(text[i - 1]);
        if (opensHere && !noClose.has(key)) {
          let close = text.indexOf(delimiter, i + delimiter.length);
          // A single `*` must not close on the first half of a `**`.
          while (!double && close !== -1 && text[close + 1] === char) {
            close = text.indexOf(delimiter, close + 2);
          }
          if (close === -1) {
            noClose.add(key);
          } else {
            const content = text.slice(i + delimiter.length, close);
            const closes = char === "*" || !isAlnum(text[close + delimiter.length]);
            if (
              content &&
              !isSpace(content[0]) &&
              !isSpace(content[content.length - 1]) &&
              closes
            ) {
              flush();
              out.push({
                type: double ? "strong" : "em",
                children: parseInlineAt(content, depth + 1),
              });
              i = close + delimiter.length;
              continue;
            }
          }
        }
      }

      if (
        char === "h" &&
        (text.startsWith("http://", i) || text.startsWith("https://", i)) &&
        !isAlnum(text[i - 1])
      ) {
        let end = i;
        while (end < text.length && !/[\s<>"'`]/.test(text[end] as string)) end += 1;
        // Trailing punctuation belongs to the sentence, not to the address.
        while (end > i && ".,;:!?)]}".includes(text[end - 1] as string)) end -= 1;
        const candidate = text.slice(i, end);
        const href = safeHttpUrl(candidate);
        if (href && candidate.length > "https://".length) {
          flush();
          out.push({ type: "link", href, children: [{ type: "text", value: candidate }] });
          i = end;
          continue;
        }
      }
    }

    buffer += char;
    i += 1;
  }
  flush();
  return out;
}

/** Inline formatting of one block of text; line breaks become `br`. */
export function parseInline(text: string): Inline[] {
  if (text.length > MAX_MARKDOWN_CHARS) return plainInlines(text);
  return parseInlineAt(text, 0);
}

interface ListItemLine {
  ordered: boolean;
  text: string;
}

/** `- item`, `* item`, `+ item`, `1. item`, `1) item` (not `**bold**`). */
function listItem(line: string): ListItemLine | null {
  const trimmed = line.trimStart();
  const first = trimmed[0];
  if ((first === "-" || first === "*" || first === "+") && trimmed[1] === " ") {
    return { ordered: false, text: trimmed.slice(2).trim() };
  }
  let digits = 0;
  while (digits < trimmed.length && digits < 9 && /\d/.test(trimmed[digits] as string)) digits += 1;
  if (
    digits > 0 &&
    (trimmed[digits] === "." || trimmed[digits] === ")") &&
    trimmed[digits + 1] === " "
  ) {
    return { ordered: true, text: trimmed.slice(digits + 2).trim() };
  }
  return null;
}

/** An opening or closing code fence: three or more backticks (or tildes) alone on the line. */
function fenceOf(line: string): string | null {
  const trimmed = line.trim();
  const char = trimmed[0];
  if (char !== "`" && char !== "~") return null;
  let length = 0;
  while (trimmed[length] === char) length += 1;
  if (length < 3) return null;
  // The info string after an opening fence (```ts) is ignored; a backtick fence cannot have ticks.
  const rest = trimmed.slice(length);
  if (char === "`" && rest.includes("`")) return null;
  return char.repeat(length);
}

const isFenceClose = (line: string, fence: string): boolean => {
  const trimmed = line.trim();
  return trimmed.length >= fence.length && trimmed === (fence[0] as string).repeat(trimmed.length);
};

/** `# Title` is shown as a bold line: reviews are not documents, they do not need big headings. */
function headingText(line: string): string | null {
  let hashes = 0;
  while (line[hashes] === "#") hashes += 1;
  if (hashes < 1 || hashes > 6 || line[hashes] !== " ") return null;
  return line.slice(hashes + 1).trim() || null;
}

export function parseMarkdown(source: string): Block[] {
  const text = source.replace(/\r\n?/g, "\n");
  if (text.length > MAX_MARKDOWN_CHARS) {
    return [{ type: "paragraph", children: plainInlines(text) }];
  }
  const lines = text.split("\n");
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i] as string;

    const fence = fenceOf(line);
    if (fence) {
      const body: string[] = [];
      i += 1;
      while (i < lines.length && !isFenceClose(lines[i] as string, fence)) {
        body.push(lines[i] as string);
        i += 1;
      }
      i += 1; // The closing fence (an unclosed block runs to the end).
      blocks.push({ type: "code", value: body.join("\n") });
      continue;
    }

    if (!line.trim()) {
      i += 1;
      continue;
    }

    const heading = headingText(line);
    if (heading) {
      blocks.push({
        type: "paragraph",
        children: [{ type: "strong", children: parseInlineAt(heading, 1) }],
      });
      i += 1;
      continue;
    }

    const first = listItem(line);
    if (first) {
      const items: string[] = [first.text];
      i += 1;
      while (i < lines.length) {
        const next = lines[i] as string;
        const item = listItem(next);
        if (item && item.ordered === first.ordered) {
          items.push(item.text);
          i += 1;
        } else if (!next.trim()) {
          // A blank line keeps the list going only when the next item continues it.
          let peek = i + 1;
          while (peek < lines.length && !(lines[peek] as string).trim()) peek += 1;
          const after = peek < lines.length ? listItem(lines[peek] as string) : null;
          if (after && after.ordered === first.ordered) i = peek;
          else break;
        } else if (!item && !fenceOf(next) && /^\s{2,}/.test(next)) {
          items[items.length - 1] += `\n${next.trim()}`;
          i += 1;
        } else {
          break;
        }
      }
      blocks.push({
        type: "list",
        ordered: first.ordered,
        items: items.map((item) => parseInlineAt(item, 0)),
      });
      continue;
    }

    const paragraph: string[] = [line.trim()];
    i += 1;
    while (i < lines.length) {
      const next = lines[i] as string;
      if (!next.trim() || fenceOf(next) || listItem(next) || headingText(next)) break;
      paragraph.push(next.trim());
      i += 1;
    }
    blocks.push({ type: "paragraph", children: parseInlineAt(paragraph.join("\n"), 0) });
  }
  return blocks;
}

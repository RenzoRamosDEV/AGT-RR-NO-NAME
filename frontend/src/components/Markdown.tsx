import type { ReactNode } from "react";
import { type Block, type Inline, parseMarkdown } from "../lib/markdown";

function renderInline(nodes: Inline[], keyPrefix: string): ReactNode[] {
  return nodes.map((node, index) => {
    const key = `${keyPrefix}.${index}`;
    switch (node.type) {
      case "text":
        return node.value;
      case "br":
        return <br key={key} />;
      case "code":
        return (
          <code key={key} className="md-code">
            {node.value}
          </code>
        );
      case "strong":
        return <strong key={key}>{renderInline(node.children, key)}</strong>;
      case "em":
        return <em key={key}>{renderInline(node.children, key)}</em>;
      case "link":
        // `href` already passed `safeHttpUrl` in the parser: it is always http or https.
        return (
          <a key={key} href={node.href} target="_blank" rel="noopener noreferrer nofollow">
            {renderInline(node.children, key)}
          </a>
        );
    }
  });
}

function renderBlock(block: Block, index: number): ReactNode {
  switch (block.type) {
    case "paragraph":
      return <p key={index}>{renderInline(block.children, String(index))}</p>;
    case "code":
      return (
        <pre key={index} className="md-pre">
          <code>{block.value}</code>
        </pre>
      );
    case "list": {
      const Tag = block.ordered ? "ol" : "ul";
      return (
        <Tag key={index}>
          {block.items.map((item, itemIndex) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: the list is rebuilt from text on each render
            <li key={itemIndex}>{renderInline(item, `${index}.${itemIndex}`)}</li>
          ))}
        </Tag>
      );
    }
  }
}

/**
 * Agent text with a little formatting (see `lib/markdown.ts`). Everything goes through React, so
 * nothing in the text can become HTML; links are only http(s).
 */
export function Markdown({ text, className }: { text: string; className?: string }) {
  const blocks = parseMarkdown(text);
  if (blocks.length === 0) return null;
  return (
    <div className={className ? `md ${className}` : "md"}>
      {blocks.map((block, index) => renderBlock(block, index))}
    </div>
  );
}

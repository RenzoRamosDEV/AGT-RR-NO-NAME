import { describe, expect, it } from "vitest";
import { DEFAULT_API_URL, ingestCommand } from "./ingestHint";

describe("ingestCommand", () => {
  it("targets the commit endpoint with the slug and a token placeholder", () => {
    const cmd = ingestCommand("acme/widgets", "https://api.example.com/");
    expect(cmd).toContain("https://api.example.com/ingest/commit");
    expect(cmd).toContain('"project":"acme/widgets"');
    expect(cmd).toContain('"X-Ingest-Token: $INGEST_TOKEN"');
  });

  it("falls back to the local API when none is configured", () => {
    expect(ingestCommand("p", undefined)).toContain(`${DEFAULT_API_URL}/ingest/commit`);
    expect(ingestCommand("p", "")).toContain(`${DEFAULT_API_URL}/ingest/commit`);
  });

  it("keeps a quote in the slug from breaking out of the shell string", () => {
    const cmd = ingestCommand("a'b", undefined);
    expect(cmd).toContain("a'\\''b");
  });
});

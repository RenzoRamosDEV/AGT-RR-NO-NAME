import { afterEach, describe, expect, it, vi } from "vitest";
import { copyText } from "./clipboard";

afterEach(() => {
  vi.restoreAllMocks();
  Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
});

function setClipboard(writeText: (t: string) => Promise<void>) {
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
}

describe("copyText", () => {
  it("uses the Clipboard API when available", async () => {
    const writeText = vi.fn(async () => {});
    setClipboard(writeText);
    expect(await copyText("abc")).toBe(true);
    expect(writeText).toHaveBeenCalledWith("abc");
  });

  it("falls back to execCommand when the Clipboard API rejects", async () => {
    setClipboard(async () => {
      throw new Error("denied");
    });
    const exec = vi.fn(() => true);
    document.execCommand = exec;
    expect(await copyText("abc")).toBe(true);
    expect(exec).toHaveBeenCalledWith("copy");
    expect(document.querySelector("textarea")).toBeNull();
  });

  it("reports failure when neither path works", async () => {
    document.execCommand = vi.fn(() => false);
    expect(await copyText("abc")).toBe(false);
  });
});

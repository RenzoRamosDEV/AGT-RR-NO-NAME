import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { clearIngestToken, getIngestToken, setIngestToken, useIngestToken } from "./ingestToken";

afterEach(clearIngestToken);

describe("ingest token store", () => {
  it("shares the value between hooks and clears it", () => {
    const a = renderHook(() => useIngestToken());
    const b = renderHook(() => useIngestToken());
    act(() => a.result.current[1]("secreto"));
    expect(b.result.current[0]).toBe("secreto");
    act(() => clearIngestToken());
    expect(a.result.current[0]).toBe("");
    expect(getIngestToken()).toBe("");
  });

  it("never writes to web storage", () => {
    const local = vi.spyOn(Storage.prototype, "setItem");
    setIngestToken("secreto");
    expect(local).not.toHaveBeenCalled();
    expect(JSON.stringify({ ...localStorage, ...sessionStorage })).not.toContain("secreto");
  });
});

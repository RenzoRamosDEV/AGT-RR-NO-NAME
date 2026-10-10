import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAsync } from "./useAsync";

const flush = (ms: number) =>
  act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

function setVisibility(state: "visible" | "hidden") {
  vi.spyOn(document, "visibilityState", "get").mockReturnValue(state);
  document.dispatchEvent(new Event("visibilitychange"));
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("useAsync polling", () => {
  it("refreshes in the background without going back to loading", async () => {
    let n = 0;
    const load = vi.fn(async () => ++n);
    const statuses: string[] = [];
    const { result } = renderHook(() => {
      const r = useAsync(load, { pollMs: 1000 });
      statuses.push(r.status);
      return r;
    });
    await flush(0);
    expect(result.current).toMatchObject({ status: "ready", data: 1 });

    await flush(1000);
    expect(result.current).toMatchObject({ status: "ready", data: 2 });
    await flush(1000);
    expect(result.current).toMatchObject({ status: "ready", data: 3 });
    // After the first load every render stays "ready": the refreshes never flash a loading state.
    expect(statuses.slice(statuses.indexOf("ready")).every((s) => s === "ready")).toBe(true);
  });

  it("does not poll without a period", async () => {
    const load = vi.fn(async () => 1);
    renderHook(() => useAsync(load));
    await flush(60_000);
    expect(load).toHaveBeenCalledTimes(1);
  });

  it("keeps the same object when the refreshed value is equal", async () => {
    const load = vi.fn(async () => ({ items: [1, 2] }));
    const { result } = renderHook(() =>
      useAsync(load, { pollMs: 1000, equals: (a, b) => a.items.join() === b.items.join() }),
    );
    await flush(0);
    const first = result.current.status === "ready" ? result.current.data : null;
    await flush(3000);
    expect(load).toHaveBeenCalledTimes(4);
    expect(result.current.status === "ready" && result.current.data).toBe(first);
  });

  it("does not start a request while the previous one is still running", async () => {
    const pending = deferred<number>();
    const load = vi.fn().mockResolvedValueOnce(1).mockReturnValue(pending.promise);
    renderHook(() => useAsync(load, { pollMs: 1000 }));
    await flush(0);
    await flush(5000);
    expect(load).toHaveBeenCalledTimes(2);
  });

  it("pauses while the tab is hidden and refreshes as soon as it is shown", async () => {
    const load = vi.fn(async () => 1);
    renderHook(() => useAsync(load, { pollMs: 1000 }));
    await flush(0);
    setVisibility("hidden");
    await flush(10_000);
    expect(load).toHaveBeenCalledTimes(1);

    setVisibility("visible");
    await flush(0);
    expect(load).toHaveBeenCalledTimes(2);
  });

  it("stops polling once pollWhile says the data is final", async () => {
    let n = 0;
    const load = vi.fn(async () => ++n);
    const { result } = renderHook(() => useAsync(load, { pollMs: 1000, pollWhile: (d) => d < 3 }));
    await flush(0);
    for (let i = 0; i < 10; i++) await flush(1000);
    expect(result.current).toMatchObject({ status: "ready", data: 3 });
    expect(load).toHaveBeenCalledTimes(3);
  });

  it("ignores a background response that belongs to a previous load", async () => {
    const late = deferred<string>();
    const loadA = vi.fn().mockResolvedValueOnce("a1").mockReturnValue(late.promise);
    const loadB = vi.fn(async () => "b1");
    const { result, rerender } = renderHook(({ load }) => useAsync(load, { pollMs: 1000 }), {
      initialProps: { load: loadA as () => Promise<string> },
    });
    await flush(0);
    await flush(1000);
    expect(loadA).toHaveBeenCalledTimes(2);

    rerender({ load: loadB });
    await flush(0);
    expect(result.current).toMatchObject({ status: "ready", data: "b1" });

    late.resolve("a2");
    await flush(0);
    expect(result.current).toMatchObject({ status: "ready", data: "b1" });
  });

  it("keeps the data and flags the failure when a refresh fails, then recovers", async () => {
    const load = vi
      .fn()
      .mockResolvedValueOnce("ok")
      .mockRejectedValueOnce(new Error("down"))
      .mockResolvedValue("again");
    const { result } = renderHook(() => useAsync(load, { pollMs: 1000 }));
    await flush(0);
    await flush(1000);
    expect(result.current).toMatchObject({ status: "ready", data: "ok", refreshFailed: true });

    await flush(1000);
    expect(result.current).toMatchObject({ status: "ready", data: "again", refreshFailed: false });
  });

  it("refresh() reloads silently even without polling", async () => {
    let n = 0;
    const load = vi.fn(async () => ++n);
    const { result } = renderHook(() => useAsync(load));
    await flush(0);
    act(() => result.current.refresh());
    await flush(0);
    expect(result.current).toMatchObject({ status: "ready", data: 2 });
  });

  it("does not leave the error state on its own", async () => {
    const load = vi.fn().mockRejectedValueOnce(new Error("boom")).mockResolvedValue("ok");
    const { result } = renderHook(() => useAsync(load, { pollMs: 1000 }));
    await flush(5000);
    expect(result.current.status).toBe("error");
    expect(load).toHaveBeenCalledTimes(1);
    act(() => result.current.retry());
    await flush(0);
    expect(result.current).toMatchObject({ status: "ready", data: "ok" });
  });
});

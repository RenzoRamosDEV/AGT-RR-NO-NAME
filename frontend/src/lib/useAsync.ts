import { useCallback, useEffect, useRef, useState } from "react";

export type AsyncState<T> =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; data: T };

export interface AsyncOptions<T> {
  /** Silent refresh period in ms; `0` or absent disables polling. */
  pollMs?: number;
  /** Polling continues only while this returns true for the data currently shown. */
  pollWhile?: (data: T) => boolean;
  /** A refresh that returns an equal value keeps the previous object (no re-render, no flicker). */
  equals?: (previous: T, next: T) => boolean;
}

export interface AsyncResult {
  retry: () => void;
  /** Reloads in the background right now: no loading state, previous data stays on failure. */
  refresh: () => void;
  /** When the data shown was last loaded, as epoch ms; `null` until the first load. */
  updatedAt: number | null;
  /** The last background refresh failed; the previous data is still shown. */
  refreshFailed: boolean;
}

/**
 * Runs `load` whenever it changes; stale responses are ignored. `retry` reruns it from scratch
 * (back to loading). With `pollMs` it also refreshes in the background: never overlapping, paused
 * while the tab is hidden and refreshing as soon as it is shown again.
 */
export function useAsync<T>(
  load: () => Promise<T>,
  options: AsyncOptions<T> = {},
): AsyncState<T> & AsyncResult {
  const { pollMs = 0 } = options;
  const [state, setState] = useState<AsyncState<T>>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);
  const [refreshFailed, setRefreshFailed] = useState(false);

  // Latest values for the long-lived polling callbacks, so they never read stale closures.
  const latest = useRef({ state, options });
  latest.current = { state, options };
  const refreshNow = useRef<(force: boolean) => void>(() => {});

  // biome-ignore lint/correctness/useExhaustiveDependencies: `attempt` re-triggers the load on retry
  useEffect(() => {
    let current = true;
    setState({ status: "loading" });
    setUpdatedAt(null);
    setRefreshFailed(false);
    load().then(
      (data) => {
        if (!current) return;
        setState({ status: "ready", data });
        setUpdatedAt(Date.now());
      },
      (error) => current && setState({ status: "error", error }),
    );
    return () => {
      current = false;
    };
  }, [load, attempt]);

  // biome-ignore lint/correctness/useExhaustiveDependencies: `attempt` restarts polling after a retry
  useEffect(() => {
    let current = true;
    let inFlight = false;

    async function refresh(force: boolean) {
      if (!current || inFlight) return;
      if (!force && document.visibilityState === "hidden") return;
      const { state: shown, options: opts } = latest.current;
      if (shown.status !== "ready") return;
      if (!force && opts.pollWhile && !opts.pollWhile(shown.data)) return;
      inFlight = true;
      try {
        const data = await load();
        if (!current) return;
        const equals = latest.current.options.equals;
        setState((prev) =>
          prev.status === "ready" && equals?.(prev.data, data) ? prev : { status: "ready", data },
        );
        setUpdatedAt(Date.now());
        setRefreshFailed(false);
      } catch {
        if (current) setRefreshFailed(true);
      } finally {
        inFlight = false;
      }
    }

    refreshNow.current = (force) => void refresh(force);
    if (pollMs <= 0) {
      return () => {
        current = false;
      };
    }
    const timer = setInterval(() => void refresh(false), pollMs);
    const onVisibility = () => {
      if (document.visibilityState === "visible") void refresh(false);
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      current = false;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [load, attempt, pollMs]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  const refresh = useCallback(() => refreshNow.current(true), []);
  return { ...state, retry, refresh, updatedAt, refreshFailed };
}

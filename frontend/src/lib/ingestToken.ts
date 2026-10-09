import { useSyncExternalStore } from "react";

/**
 * The ingest token lives only in this module's memory: it survives navigation inside the tab and
 * disappears on reload. It is never written to storage, the URL or the build.
 */
let token = "";
const listeners = new Set<() => void>();

function emit() {
  for (const listener of listeners) listener();
}

export function getIngestToken(): string {
  return token;
}

export function setIngestToken(value: string): void {
  if (value === token) return;
  token = value;
  emit();
}

export function clearIngestToken(): void {
  setIngestToken("");
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useIngestToken(): [string, (value: string) => void] {
  return [useSyncExternalStore(subscribe, getIngestToken), setIngestToken];
}

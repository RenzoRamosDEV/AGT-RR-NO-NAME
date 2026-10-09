import { type ReactNode, createContext, useContext } from "react";

/** How often the live pages refresh in the background (ms). */
export const DEFAULT_POLL_MS = 5000;

const PollingContext = createContext(0);

/**
 * Provides the background refresh period. Without a provider polling is off, so tests that do not
 * care about it are unaffected and the ones that do pick their own (small) period.
 */
export function PollingProvider({
  intervalMs = DEFAULT_POLL_MS,
  children,
}: {
  intervalMs?: number;
  children: ReactNode;
}) {
  return <PollingContext.Provider value={intervalMs}>{children}</PollingContext.Provider>;
}

export function usePollMs(): number {
  return useContext(PollingContext);
}

import { type ReactNode, createContext, useContext, useEffect, useState } from "react";

const REFRESH_MS = 60_000;

const NowContext = createContext<Date | null>(null);

/**
 * Provides the current instant for relative times. Tests pass a fixed `now`; otherwise it
 * refreshes once a minute, which is the resolution "hace 12 min" needs.
 */
export function NowProvider({ now, children }: { now?: Date; children: ReactNode }) {
  const [tick, setTick] = useState(() => new Date());
  useEffect(() => {
    if (now) return;
    const timer = setInterval(() => setTick(new Date()), REFRESH_MS);
    return () => clearInterval(timer);
  }, [now]);
  return <NowContext.Provider value={now ?? tick}>{children}</NowContext.Provider>;
}

export function useNow(): Date {
  const provided = useContext(NowContext);
  return provided ?? new Date();
}

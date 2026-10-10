import type { ReactNode } from "react";
import { ApiError } from "../lib/api";
import type { AsyncState } from "../lib/useAsync";
import { type Activity, Busy } from "./Busy";
import { Button } from "./ui/Button";

interface Props<T> {
  state: AsyncState<T> & { retry: () => void };
  loadingLabel: string;
  /** What the loading is doing, which picks the orb; a plain load by default. */
  activity?: Activity;
  /** Shown instead of the generic error when the request answered 404. */
  notFound?: ReactNode;
  children: (data: T) => ReactNode;
}

/** Renders loading / recoverable error / not found around a loaded value. */
export function AsyncBoundary<T>({
  state,
  loadingLabel,
  activity = "load",
  notFound,
  children,
}: Props<T>) {
  if (state.status === "loading") {
    return <Busy activity={activity} label={loadingLabel} />;
  }
  if (state.status === "error") {
    if (notFound && state.error instanceof ApiError && state.error.notFound) return <>{notFound}</>;
    return (
      <div className="notice" role="alert">
        <p>{state.error instanceof Error ? state.error.message : "Ocurrió un error inesperado."}</p>
        <Button onClick={state.retry}>Reintentar</Button>
      </div>
    );
  }
  return <>{children(state.data)}</>;
}

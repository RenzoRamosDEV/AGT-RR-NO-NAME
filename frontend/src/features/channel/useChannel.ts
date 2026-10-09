import { useCallback, useRef, useState } from "react";
import type { Change, ChangeKind } from "../../data/mock";
import { useDataSource } from "../../data/source";
import type { ChangePage } from "../../lib/api";
import { type StateFilter, statusesFor } from "../../lib/channelQuery";
import { mergeUnique } from "../../lib/pagination";
import { useAsync } from "../../lib/useAsync";

interface More {
  base: ChangePage;
  items: Change[];
  cursor: string | null;
  state: "idle" | "loading" | "error";
}

export interface ChannelFilters {
  kind: ChangeKind | undefined;
  state: StateFilter;
  /** Search text; blank means no search. Debounce it before passing it in. */
  q: string;
}

/**
 * First page of a project's channel plus cursor pagination. Every filter is resolved by the
 * server. Extra pages are tied to the first page they were loaded for, so changing project or any
 * filter (or retrying) discards them, and a late response for an old filter is ignored.
 */
export function useChannel(slug: string, { kind, state, q }: ChannelFilters) {
  const source = useDataSource();
  const first = useAsync(
    useCallback(
      () => source.changes(slug, { kind, status: statusesFor(state), q: q || undefined }),
      [source, slug, kind, state, q],
    ),
  );
  const [more, setMore] = useState<More | null>(null);

  const base = first.status === "ready" ? first.data : null;
  const currentBase = useRef(base);
  currentBase.current = base;
  const active = base && more?.base === base ? more : null;
  const items = base ? mergeUnique(base.items, active?.items ?? []) : [];
  const cursor = base ? (active ? active.cursor : base.nextCursor) : null;

  async function loadMore() {
    if (!base || !cursor) return;
    const previous = active?.items ?? [];
    setMore({ base, items: previous, cursor, state: "loading" });
    try {
      const page = await source.changes(slug, {
        kind,
        status: statusesFor(state),
        q: q || undefined,
        cursor,
      });
      if (currentBase.current !== base) return;
      setMore({
        base,
        items: mergeUnique(previous, page.items),
        cursor: page.nextCursor,
        state: "idle",
      });
    } catch {
      if (currentBase.current !== base) return;
      setMore({ base, items: previous, cursor, state: "error" });
    }
  }

  return { first, items, hasMore: cursor !== null, moreState: active?.state ?? "idle", loadMore };
}

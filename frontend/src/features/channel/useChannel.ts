import { useCallback, useRef, useState } from "react";
import type { Change, ChangeKind } from "../../data/mock";
import { useDataSource } from "../../data/source";
import type { ChangePage } from "../../lib/api";
import { type StateFilter, statusesFor } from "../../lib/channelQuery";
import { sameValue } from "../../lib/equal";
import { mergeUnique } from "../../lib/pagination";
import { usePollMs } from "../../lib/polling";
import { type AsyncResult, type AsyncState, useAsync } from "../../lib/useAsync";

/** A first page tagged with the query it answers, so a stale page is never shown for a new one. */
interface Tagged {
  key: string;
  page: ChangePage;
}

interface More {
  /** Query the extra pages belong to; a different query discards them. */
  key: string;
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
 * server. The first page refreshes in the background; extra pages and the items already shown are
 * tied to the query (project and filters), not to the first page object, so a refresh that brings
 * a new change keeps everything loaded: the items the new first page no longer covers are kept
 * right after it, so none is lost or repeated. Changing project or any filter discards them, and a
 * late response for an old query is ignored.
 */
export function useChannel(slug: string, { kind, state, q }: ChannelFilters) {
  const source = useDataSource();
  const pollMs = usePollMs();
  const key = JSON.stringify([slug, kind, state, q]);
  const tagged = useAsync(
    useCallback(
      async () => ({
        key,
        page: await source.changes(slug, { kind, status: statusesFor(state), q: q || undefined }),
      }),
      [source, slug, kind, state, q, key],
    ),
    { pollMs, equals: (a: Tagged, b: Tagged) => sameValue(a, b) },
  );
  const [more, setMore] = useState<More | null>(null);
  const shown = useRef<{ key: string; items: Change[] }>({ key, items: [] });
  const currentKey = useRef(key);
  currentKey.current = key;

  // Right after a filter change the hook still holds the old query's page for one render.
  const base = tagged.status === "ready" && tagged.data.key === key ? tagged.data.page : null;
  const { retry, refresh, updatedAt, refreshFailed } = tagged;
  const meta = { retry, refresh, updatedAt, refreshFailed };
  const first: AsyncState<ChangePage> & AsyncResult =
    tagged.status !== "ready"
      ? { ...tagged }
      : base
        ? { status: "ready", data: base, ...meta }
        : { status: "loading", ...meta };
  const active = more?.key === key ? more : null;
  let items: Change[] = [];
  if (base) {
    const previous = shown.current.key === key ? shown.current.items : [];
    items = mergeUnique(mergeUnique(base.items, previous), active?.items ?? []);
    shown.current = { key, items };
  }
  const cursor = base ? (active ? active.cursor : base.nextCursor) : null;

  async function loadMore() {
    if (!base || !cursor) return;
    const previous = active?.items ?? [];
    setMore({ key, items: previous, cursor, state: "loading" });
    try {
      const page = await source.changes(slug, {
        kind,
        status: statusesFor(state),
        q: q || undefined,
        cursor,
      });
      if (currentKey.current !== key) return;
      setMore({
        key,
        items: mergeUnique(previous, page.items),
        cursor: page.nextCursor,
        state: "idle",
      });
    } catch {
      if (currentKey.current !== key) return;
      setMore({ key, items: previous, cursor, state: "error" });
    }
  }

  return { first, items, hasMore: cursor !== null, moreState: active?.state ?? "idle", loadMore };
}

import { useCallback, useState } from "react";
import type { Change, ChangeKind } from "../../data/mock";
import { useDataSource } from "../../data/source";
import type { ChangePage } from "../../lib/api";
import { mergeUnique } from "../../lib/pagination";
import { useAsync } from "../../lib/useAsync";

interface More {
  base: ChangePage;
  items: Change[];
  cursor: string | null;
  state: "idle" | "loading" | "error";
}

/**
 * First page of a project's channel plus cursor pagination. Extra pages are tied to the first
 * page they were loaded for, so changing project/filter (or retrying) discards them.
 */
export function useChannel(slug: string, kind: ChangeKind | undefined) {
  const source = useDataSource();
  const first = useAsync(useCallback(() => source.changes(slug, { kind }), [source, slug, kind]));
  const [more, setMore] = useState<More | null>(null);

  const base = first.status === "ready" ? first.data : null;
  const active = base && more?.base === base ? more : null;
  const items = base ? mergeUnique(base.items, active?.items ?? []) : [];
  const cursor = base ? (active ? active.cursor : base.nextCursor) : null;

  async function loadMore() {
    if (!base || !cursor) return;
    const previous = active?.items ?? [];
    setMore({ base, items: previous, cursor, state: "loading" });
    try {
      const page = await source.changes(slug, { kind, cursor });
      setMore({
        base,
        items: mergeUnique(previous, page.items),
        cursor: page.nextCursor,
        state: "idle",
      });
    } catch {
      setMore({ base, items: previous, cursor, state: "error" });
    }
  }

  return { first, items, hasMore: cursor !== null, moreState: active?.state ?? "idle", loadMore };
}

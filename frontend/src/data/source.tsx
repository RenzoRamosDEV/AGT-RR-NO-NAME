import { type ReactNode, createContext, useContext } from "react";
import { ApiError, type ChangePage, type DataSource, createHttpSource } from "../lib/api";
import { aggregateStatus, isRetryable } from "../lib/reviewStatus";
import { matchesQuery } from "../lib/search";
import { type Change, agentStats, findChange, findProject, health, projects } from "./mock";

const DEFAULT_PAGE_SIZE = 50;

/**
 * Serves the sample data with the same contract as the API: cursor = offset, the same `kind`,
 * `status` and `q` filters, an aggregate `reviewStatus` and a retry that restarts the change
 * (kept per source, so the shared sample data is never mutated).
 */
export function createMockSource(): DataSource {
  const restarted = new Map<string, number>();

  function view(change: Change): Change {
    const run = restarted.get(change.id);
    const base = run === undefined ? change : { ...change, reviews: [], run };
    return { ...base, run: base.run ?? 1, reviewStatus: aggregateStatus(base.reviews ?? []) };
  }

  function find(id: string): Change | undefined {
    const change = projects.map((p) => findChange(p, id)).find((c) => c !== undefined);
    return change && view(change);
  }

  return {
    async projects() {
      return projects.map((p) => ({ slug: p.slug, name: p.name }));
    },
    async changes(slug, { kind, status, q, cursor, limit = DEFAULT_PAGE_SIZE } = {}) {
      const project = findProject(slug);
      if (!project) throw new ApiError("Proyecto no encontrado.", 404);
      const all = project.changes
        .map(view)
        .filter((c) => !kind || c.kind === kind)
        .filter((c) => !status?.length || (c.reviewStatus && status.includes(c.reviewStatus)))
        .filter((c) => !q || matchesQuery(c, q));
      const start = cursor ? Number(cursor) : 0;
      const items = all.slice(start, start + limit);
      const end = start + items.length;
      return { items, nextCursor: end < all.length ? String(end) : null } satisfies ChangePage;
    },
    async change(id) {
      const change = find(id);
      if (!change) throw new ApiError("Change no encontrado.", 404);
      return change;
    },
    async agentStats() {
      return agentStats;
    },
    async health() {
      return health;
    },
    async retry(id, token) {
      if (!token.trim()) throw new ApiError("Token no válido.", 401);
      const change = find(id);
      if (!change) throw new ApiError("Change no encontrado.", 404);
      if (!isRetryable(change.reviewStatus)) throw new ApiError("Nada que reintentar.", 409);
      const run = (change.run ?? 1) + 1;
      restarted.set(id, run);
      return { changeId: id, run };
    },
  };
}

const apiUrl: string | undefined = import.meta.env.VITE_API_URL;
const defaultSource: DataSource = apiUrl ? createHttpSource(apiUrl) : createMockSource();

const DataSourceContext = createContext<DataSource>(defaultSource);

export function DataSourceProvider({
  source,
  children,
}: {
  source: DataSource;
  children: ReactNode;
}) {
  return <DataSourceContext.Provider value={source}>{children}</DataSourceContext.Provider>;
}

export function useDataSource(): DataSource {
  return useContext(DataSourceContext);
}

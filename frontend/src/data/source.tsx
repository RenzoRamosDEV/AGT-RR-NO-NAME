import { type ReactNode, createContext, useCallback, useContext } from "react";
import {
  ApiError,
  type ChangePage,
  type DataSource,
  type ProjectRef,
  createHttpSource,
} from "../lib/api";
import { isAbsolutePath, slugFromPath } from "../lib/localPath";
import { aggregateStatus, isRetryable } from "../lib/reviewStatus";
import { matchesQuery } from "../lib/search";
import { useAsync } from "../lib/useAsync";
import { type Change, agentStats, findChange, findProject, health, projects } from "./mock";

const DEFAULT_PAGE_SIZE = 50;

/**
 * Serves the sample data with the same contract as the API: cursor = offset, the same `kind`,
 * `status` and `q` filters, an aggregate `reviewStatus`, a retry that restarts the change and
 * in-memory project management with the same error rules (401 without token, 422 for a relative
 * path, 409 for a duplicate, 503 when syncing a project that is not on GitHub). Everything is kept
 * per source, so the shared sample data is never mutated.
 */
export function createMockSource(): DataSource {
  const restarted = new Map<string, number>();
  const added: ProjectRef[] = [];
  const removed = new Set<string>();

  function currentProjects(): ProjectRef[] {
    const base = projects.map((p) => ({ slug: p.slug, name: p.name }));
    return [...base, ...added].filter((p) => !removed.has(p.slug));
  }

  function requireToken(token: string) {
    if (!token.trim()) throw new ApiError("Token no válido.", 401);
  }

  function view(change: Change): Change {
    const run = restarted.get(change.id);
    const base = run === undefined ? change : { ...change, reviews: [], run };
    return {
      ...base,
      run: base.run ?? 1,
      reviewStatus: aggregateStatus(base.reviews ?? [], health.agentNames.length),
    };
  }

  function find(id: string): Change | undefined {
    const change = projects.map((p) => findChange(p, id)).find((c) => c !== undefined);
    return change && view(change);
  }

  return {
    async projects() {
      return currentProjects();
    },
    async changes(slug, { kind, status, q, cursor, limit = DEFAULT_PAGE_SIZE } = {}) {
      if (!currentProjects().some((p) => p.slug === slug)) {
        throw new ApiError("Proyecto no encontrado.", 404);
      }
      const project = findProject(slug);
      const all = (project?.changes ?? [])
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
    async addProject(path, token) {
      requireToken(token);
      if (!isAbsolutePath(path)) throw new ApiError("La ruta debe ser absoluta.", 422);
      const slug = slugFromPath(path);
      if (!slug) throw new ApiError("La ruta no es un repositorio.", 422);
      if (currentProjects().some((p) => p.slug === slug)) {
        throw new ApiError("El proyecto ya existe.", 409);
      }
      removed.delete(slug);
      const project: ProjectRef = {
        slug,
        name: slug,
        path: path.trim(),
        hooksInstalled: true,
        github: false,
      };
      added.push(project);
      return project;
    },
    async removeProject(slug, token) {
      requireToken(token);
      if (!currentProjects().some((p) => p.slug === slug)) {
        throw new ApiError("Proyecto no encontrado.", 404);
      }
      const index = added.findIndex((p) => p.slug === slug);
      if (index >= 0) added.splice(index, 1);
      else removed.add(slug);
    },
    async syncPrs(slug, token) {
      requireToken(token);
      const project = currentProjects().find((p) => p.slug === slug);
      if (!project) throw new ApiError("Proyecto no encontrado.", 404);
      if (!project.github) {
        throw new ApiError("GitHub CLI (`gh`) no está disponible o no has iniciado sesión.", 503);
      }
      return { synced: 0, created: 0 };
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

/** Agents configured in the backend, or `null` while unknown (loading or the server fails). */
export function useAgentNames(): string[] | null {
  const source = useDataSource();
  const state = useAsync(useCallback(() => source.health(), [source]));
  return state.status === "ready" ? state.data.agentNames : null;
}

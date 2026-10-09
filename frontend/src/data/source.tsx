import { type ReactNode, createContext, useContext } from "react";
import { ApiError, type ChangePage, type DataSource, createHttpSource } from "../lib/api";
import { findChange, findProject, projects } from "./mock";

const DEFAULT_PAGE_SIZE = 50;

/** Serves the sample data with the same pagination contract as the API (cursor = offset). */
export function createMockSource(): DataSource {
  return {
    async projects() {
      return projects.map((p) => ({ slug: p.slug, name: p.name }));
    },
    async changes(slug, { kind, cursor, limit = DEFAULT_PAGE_SIZE } = {}): Promise<ChangePage> {
      const project = findProject(slug);
      if (!project) throw new ApiError("Proyecto no encontrado.", 404);
      const all = project.changes.filter((c) => !kind || c.kind === kind);
      const start = cursor ? Number(cursor) : 0;
      const items = all.slice(start, start + limit);
      const end = start + items.length;
      return { items, nextCursor: end < all.length ? String(end) : null };
    },
    async change(id) {
      const change = projects.map((p) => findChange(p, id)).find((c) => c !== undefined);
      if (!change) throw new ApiError("Change no encontrado.", 404);
      return change;
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

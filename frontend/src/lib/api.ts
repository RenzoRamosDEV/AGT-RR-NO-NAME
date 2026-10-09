import type { AgentName, Change, ChangeKind, Finding, Review } from "../data/mock";

/** Wire format of `round1-backend-api` (read endpoints). */
interface ProjectDto {
  id: string;
  slug: string;
}

interface ChangeSummaryDto {
  id: string;
  kind: ChangeKind;
  ref: string;
  head_sha: string;
  title: string;
  author: string;
  url: string;
  diff_truncated: boolean;
}

interface ReviewDto {
  id: string;
  agent: string;
  status: "completed" | "failed";
  summary: string | null;
  findings: Finding[];
}

interface ChangeDetailDto extends ChangeSummaryDto {
  diff: string;
  reviews: ReviewDto[];
}

interface ChangePageDto {
  items: ChangeSummaryDto[];
  next_cursor: string | null;
}

export interface ProjectRef {
  slug: string;
  name: string;
}

export interface ChangePage {
  items: Change[];
  nextCursor: string | null;
}

export interface ChangeQuery {
  kind?: ChangeKind;
  cursor?: string | null;
  limit?: number;
}

export interface DataSource {
  projects(): Promise<ProjectRef[]>;
  changes(slug: string, query?: ChangeQuery): Promise<ChangePage>;
  change(id: string): Promise<Change>;
}

export class ApiError extends Error {
  readonly status: number | null;

  constructor(message: string, status: number | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }

  get notFound(): boolean {
    return this.status === 404;
  }
}

const AGENTS: readonly AgentName[] = ["claude", "codex"];

function toAgent(agent: string): AgentName {
  const name = agent.toLowerCase();
  return (AGENTS as readonly string[]).includes(name) ? (name as AgentName) : "claude";
}

function toChange(dto: ChangeSummaryDto): Change {
  return {
    id: dto.id,
    kind: dto.kind,
    title: dto.title || dto.ref || dto.head_sha,
    author: dto.author,
    sha: dto.head_sha,
    ref: dto.ref,
    url: dto.url,
    diff: "",
    truncated: dto.diff_truncated,
  };
}

function toReview(dto: ReviewDto): Review {
  return {
    id: dto.id,
    agent: toAgent(dto.agent),
    status: dto.status,
    summary: dto.summary ?? undefined,
    findings: dto.findings,
  };
}

export function createHttpSource(
  baseUrl: string,
  fetchImpl: typeof fetch = (...args) => fetch(...args),
): DataSource {
  const root = baseUrl.replace(/\/+$/, "");

  async function get<T>(path: string): Promise<T> {
    let response: Response;
    try {
      response = await fetchImpl(`${root}${path}`, { headers: { Accept: "application/json" } });
    } catch {
      throw new ApiError("No se pudo conectar con el servidor.", null);
    }
    if (!response.ok) {
      throw new ApiError(`El servidor respondió ${response.status}.`, response.status);
    }
    return (await response.json()) as T;
  }

  return {
    async projects() {
      const projects = await get<ProjectDto[]>("/projects");
      return projects.map((p) => ({ slug: p.slug, name: p.slug }));
    },
    async changes(slug, { kind, cursor, limit } = {}) {
      const params = new URLSearchParams();
      if (kind) params.set("kind", kind);
      if (cursor) params.set("cursor", cursor);
      if (limit) params.set("limit", String(limit));
      const qs = params.size > 0 ? `?${params}` : "";
      // The slug may contain "/" (`owner/repo`); the backend route accepts it as a path.
      const page = await get<ChangePageDto>(
        `/projects/${slug.split("/").map(encodeURIComponent).join("/")}/changes${qs}`,
      );
      return { items: page.items.map(toChange), nextCursor: page.next_cursor };
    },
    async change(id) {
      const dto = await get<ChangeDetailDto>(`/changes/${encodeURIComponent(id)}`);
      return { ...toChange(dto), diff: dto.diff, reviews: dto.reviews.map(toReview) };
    },
  };
}

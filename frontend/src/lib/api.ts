import type {
  AgentStat,
  Change,
  ChangeKind,
  Finding,
  Health,
  Review,
  ReviewAggregate,
} from "../data/mock";

/** Wire format of `round1-backend-api` and `round2-backend-api` (read and retry endpoints). */
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
  created_at: string;
  diff_truncated: boolean;
  run?: number;
  review_status?: ReviewAggregate;
}

interface ReviewDto {
  id: string;
  agent: string;
  status: "completed" | "failed";
  summary: string | null;
  findings: Finding[];
  run?: number;
  score?: number | null;
  duration_ms?: number | null;
  error?: string | null;
}

interface AgentStatDto {
  agent: string;
  total: number;
  completed: number;
  failed: number;
  avg_duration_ms: number | null;
  avg_score: number | null;
}

interface HealthDto {
  status: "ok" | "degraded";
  dependencies: Record<
    string,
    { status: "ok" | "unavailable"; latency_ms: number; reason?: "timeout" | "error" | null }
  >;
}

interface RetryDto {
  change_id: string;
  run: number;
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
  /** Review states to keep; sent as a repeated `status` parameter. */
  status?: readonly ReviewAggregate[];
  /** Free-text search (title, author, SHA or ref); blank is ignored. */
  q?: string;
  cursor?: string | null;
  limit?: number;
}

export interface RetryResult {
  changeId: string;
  run: number;
}

export interface DataSource {
  projects(): Promise<ProjectRef[]>;
  changes(slug: string, query?: ChangeQuery): Promise<ChangePage>;
  change(id: string): Promise<Change>;
  agentStats(): Promise<AgentStat[]>;
  health(): Promise<Health>;
  /** Starts a new review run for a failed change. Rejects with `ApiError` (401/404/409/503…). */
  retry(id: string, token: string): Promise<RetryResult>;
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

function toChange(dto: ChangeSummaryDto): Change {
  return {
    id: dto.id,
    kind: dto.kind,
    title: dto.title || dto.ref || dto.head_sha,
    author: dto.author,
    sha: dto.head_sha,
    ref: dto.ref,
    url: dto.url,
    createdAt: dto.created_at,
    diff: "",
    truncated: dto.diff_truncated,
    run: dto.run,
    reviewStatus: dto.review_status,
  };
}

function toReview(dto: ReviewDto): Review {
  return {
    id: dto.id,
    agent: dto.agent,
    status: dto.status,
    summary: dto.summary ?? undefined,
    findings: dto.findings,
    run: dto.run,
    score: dto.score,
    durationMs: dto.duration_ms,
    error: dto.error,
  };
}

export function createHttpSource(
  baseUrl: string,
  fetchImpl: typeof fetch = (...args) => fetch(...args),
): DataSource {
  const root = baseUrl.replace(/\/+$/, "");

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    let response: Response;
    try {
      response = await fetchImpl(`${root}${path}`, {
        ...init,
        headers: { Accept: "application/json", ...init.headers },
      });
    } catch {
      throw new ApiError("No se pudo conectar con el servidor.", null);
    }
    if (!response.ok) {
      throw new ApiError(`El servidor respondió ${response.status}.`, response.status);
    }
    return (await response.json()) as T;
  }
  const get = <T>(path: string) => request<T>(path);

  return {
    async projects() {
      const projects = await get<ProjectDto[]>("/projects");
      return projects.map((p) => ({ slug: p.slug, name: p.slug }));
    },
    async changes(slug, { kind, status, q, cursor, limit } = {}) {
      const params = new URLSearchParams();
      if (kind) params.set("kind", kind);
      for (const value of status ?? []) params.append("status", value);
      if (q?.trim()) params.set("q", q.trim());
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
    async agentStats() {
      const rows = await get<AgentStatDto[]>("/stats/agents");
      return rows.map((r) => ({
        agent: r.agent,
        total: r.total,
        completed: r.completed,
        failed: r.failed,
        avgDurationMs: r.avg_duration_ms,
        avgScore: r.avg_score,
      }));
    },
    async health() {
      const dto = await get<HealthDto>("/health/dependencies");
      return {
        status: dto.status,
        dependencies: Object.entries(dto.dependencies)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([name, d]) => ({
            name,
            status: d.status,
            latencyMs: d.latency_ms,
            reason: d.reason ?? undefined,
          })),
      };
    },
    async retry(id, token) {
      const dto = await request<RetryDto>(`/changes/${encodeURIComponent(id)}/retry`, {
        method: "POST",
        headers: { "X-Ingest-Token": token },
      });
      return { changeId: dto.change_id, run: dto.run };
    },
  };
}

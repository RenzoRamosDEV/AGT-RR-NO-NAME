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
  /** Local path, hook state and GitHub flag come with the local-projects API (all optional). */
  path?: string | null;
  hooks_installed?: boolean | null;
  github?: boolean | string | null;
}

interface SyncPrsDto {
  synced: number;
  created: number;
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
  /** Light reviews of the current run; only the channel listing sends them. */
  reviews?: ReviewBriefDto[];
}

interface ReviewBriefDto {
  agent: string;
  status: "completed" | "failed";
  score: number | null;
  duration_ms: number | null;
  run: number;
  /** Change the review was copied from (a PR reusing its identical commit's), `null` if its own. */
  reused_from?: string | null;
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
  reused_from?: string | null;
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
  agent_names?: string[];
}

interface RetryDto {
  change_id: string;
  run: number;
}

interface ChangeDetailDto extends Omit<ChangeSummaryDto, "reviews"> {
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
  /** Absolute path of the local repository, when the project was added from disk. */
  path?: string;
  hooksInstalled?: boolean;
  /** The repository lives on GitHub, so its PRs can be synchronised. */
  github?: boolean;
}

export interface SyncResult {
  synced: number;
  created: number;
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
  /** Registers a local git repository and installs its hooks. Rejects with `ApiError`. */
  addProject(path: string, token: string): Promise<ProjectRef>;
  /** Removes a project, its hooks and its history. */
  removeProject(slug: string, token: string): Promise<void>;
  /** Imports the repository's PRs through `gh`; 503 when `gh` is missing or not logged in. */
  syncPrs(slug: string, token: string): Promise<SyncResult>;
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

function toProject(dto: ProjectDto): ProjectRef {
  return {
    slug: dto.slug,
    name: dto.slug,
    ...(dto.path ? { path: dto.path } : {}),
    ...(dto.hooks_installed != null ? { hooksInstalled: dto.hooks_installed } : {}),
    ...(dto.github != null ? { github: Boolean(dto.github) } : {}),
  };
}

/** The slug may contain "/" (`owner/repo`); the backend routes accept it as a path. */
const slugPath = (slug: string) => slug.split("/").map(encodeURIComponent).join("/");

/** FastAPI sends `detail` as text for application errors and as a list for validation errors. */
async function errorDetail(response: Response): Promise<string | null> {
  try {
    const body: unknown = await response.json();
    const detail = (body as { detail?: unknown } | null)?.detail;
    return typeof detail === "string" && detail.trim() ? detail : null;
  } catch {
    return null;
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
    ...(dto.reviews ? { reviews: dto.reviews.map((b) => toBrief(dto.id, b)) } : {}),
  };
}

/** The listing has no review ids: a change has one review per agent and run, so that is the key. */
function toBrief(changeId: string, dto: ReviewBriefDto): Review {
  return {
    id: `${changeId}:${dto.agent}:${dto.run}`,
    agent: dto.agent,
    status: dto.status,
    run: dto.run,
    score: dto.score,
    durationMs: dto.duration_ms,
    reusedFrom: dto.reused_from ?? null,
    partial: true,
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
    reusedFrom: dto.reused_from ?? null,
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
      const detail = await errorDetail(response);
      throw new ApiError(detail ?? `El servidor respondió ${response.status}.`, response.status);
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }
  const get = <T>(path: string) => request<T>(path);

  return {
    async projects() {
      const projects = await get<ProjectDto[]>("/projects");
      return projects.map(toProject);
    },
    async changes(slug, { kind, status, q, cursor, limit } = {}) {
      const params = new URLSearchParams();
      if (kind) params.set("kind", kind);
      for (const value of status ?? []) params.append("status", value);
      if (q?.trim()) params.set("q", q.trim());
      if (cursor) params.set("cursor", cursor);
      if (limit) params.set("limit", String(limit));
      const qs = params.size > 0 ? `?${params}` : "";
      const page = await get<ChangePageDto>(`/projects/${slugPath(slug)}/changes${qs}`);
      return { items: page.items.map(toChange), nextCursor: page.next_cursor };
    },
    async change(id) {
      const dto = await get<ChangeDetailDto>(`/changes/${encodeURIComponent(id)}`);
      return {
        ...toChange({ ...dto, reviews: undefined }),
        diff: dto.diff,
        reviews: dto.reviews.map(toReview),
      };
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
        agentNames: dto.agent_names ?? [],
      };
    },
    async retry(id, token) {
      const dto = await request<RetryDto>(`/changes/${encodeURIComponent(id)}/retry`, {
        method: "POST",
        headers: { "X-Ingest-Token": token },
      });
      return { changeId: dto.change_id, run: dto.run };
    },
    async addProject(path, token) {
      const dto = await request<ProjectDto>("/projects", {
        method: "POST",
        headers: { "X-Ingest-Token": token, "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      return toProject(dto);
    },
    async removeProject(slug, token) {
      await request<void>(`/projects/${slugPath(slug)}`, {
        method: "DELETE",
        headers: { "X-Ingest-Token": token },
      });
    },
    async syncPrs(slug, token) {
      const dto = await request<SyncPrsDto>(`/projects/${slugPath(slug)}/sync-prs`, {
        method: "POST",
        headers: { "X-Ingest-Token": token },
      });
      return { synced: dto.synced, created: dto.created };
    },
  };
}

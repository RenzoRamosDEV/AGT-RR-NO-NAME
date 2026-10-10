// View model shared by the UI, plus sample data used when no API is configured (VITE_API_URL).

/** Agent id as sent by the API (free text); only `claude` and `codex` have a proper display name. */
export type AgentName = string;
export type ReviewStatus = "running" | "completed" | "failed";
export type ChangeKind = "commit" | "pr";
/** Aggregate review state of a change, as reported by the API (`review_status`). */
export type ReviewAggregate = "pending" | "running" | "partial_failed" | "failed" | "completed";

export interface Finding {
  severity: string;
  file: string;
  line: number;
  message: string;
}

export interface Review {
  id: string;
  agent: AgentName;
  status: ReviewStatus;
  summary?: string;
  findings?: Finding[];
  run?: number;
  durationMs?: number | null;
  score?: number | null;
  /** Failure reason as sent by the server; sanitize it before showing it. */
  error?: string | null;
  /** Id of the change this review was copied from (a PR reusing its identical commit's). */
  reusedFrom?: string | null;
  /** Light version from the channel listing: no summary, findings or error until the detail loads. */
  partial?: boolean;
}

/**
 * What happened to a commit afterwards, as reported by the API (`commit_state`): `discarded` = it is
 * no longer on any branch of the local repository (reset, amend, rebase…); `reverted` = a later
 * commit undoes it with `git revert`. A PR is always `active`.
 */
export type CommitState = "active" | "discarded" | "reverted";

/** The commit that reverts another one, enough to name and link it. */
export interface RevertedBy {
  id: string;
  sha: string;
}

export interface Change {
  id: string;
  kind: ChangeKind;
  title: string;
  author: string;
  /** Full head SHA; use `shortSha` to display it. */
  sha: string;
  ref: string;
  url: string;
  /** ISO timestamp; absent when the source does not report it. */
  createdAt?: string;
  diff: string;
  truncated?: boolean;
  run?: number;
  reviewStatus?: ReviewAggregate;
  /** Absent (= `active`) when the source does not report it. */
  commitState?: CommitState;
  /** Set only when `commitState` is `reverted` and the reverting commit is known. */
  revertedBy?: RevertedBy;
  /** Absent when the source does not report reviews (the API channel listing). */
  reviews?: Review[];
}

export interface AgentStat {
  agent: string;
  total: number;
  completed: number;
  failed: number;
  avgDurationMs: number | null;
  avgScore: number | null;
}

export interface DependencyHealth {
  /** Machine name sent by the server, e.g. `postgres`. */
  name: string;
  status: "ok" | "unavailable";
  latencyMs: number;
  reason?: "timeout" | "error";
}

export interface Health {
  status: "ok" | "degraded";
  dependencies: DependencyHealth[];
  /** Agents configured in the backend (`AGENT_NAMES`); empty when the server does not say. */
  agentNames: string[];
}

export interface Project {
  slug: string;
  name: string;
  changes: Change[];
}

const DIFF = `@@ src/ingest.py
-    token = request.headers.get("X-Ingest-Token")
+    token = request.headers.get("X-Ingest-Token", "")
+    if not hmac.compare_digest(token, settings.ingest_token):
+        raise Unauthorized()
-    if token == settings.ingest_token:
-        return accept(request)`;

const minutesAgo = (minutes: number) => new Date(Date.now() - minutes * 60_000).toISOString();

export const projects: Project[] = [
  {
    slug: "duelo",
    name: "duelo",
    changes: [
      {
        id: "c1",
        kind: "commit",
        title: "fix: comparar el token de ingesta en tiempo constante",
        author: "renzo",
        sha: "a41f9c2",
        ref: "main",
        url: "https://github.com/RenzoRamosDEV/Duelo/commit/a41f9c2",
        createdAt: minutesAgo(12),
        diff: DIFF,
        reviews: [
          {
            id: "r1",
            agent: "claude",
            status: "completed",
            run: 1,
            durationMs: 42_000,
            score: 8,
            summary: "Cambio correcto; elimina la comparación vulnerable a timing.",
            findings: [
              {
                severity: "medium",
                file: "src/ingest.py",
                line: 3,
                message: "Falta test para token vacío.",
              },
              {
                severity: "low",
                file: "src/ingest.py",
                line: 1,
                message: "Considerar rotación del token.",
              },
            ],
          },
          { id: "r2", agent: "codex", status: "running" },
        ],
      },
      {
        // A commit that was undone with `git reset`: no longer on any branch of the repository.
        id: "c3",
        kind: "commit",
        title: "fix: ajustar el límite de peticiones por IP",
        author: "marta",
        sha: "7c1d2e8",
        ref: "main",
        url: "https://github.com/RenzoRamosDEV/Duelo/commit/7c1d2e8",
        createdAt: minutesAgo(40),
        diff: DIFF,
        commitState: "discarded",
        reviewStatus: "completed",
        reviews: [
          { id: "r5", agent: "claude", status: "completed", run: 1, durationMs: 31_000, score: 6 },
          { id: "r6", agent: "codex", status: "completed", run: 1, durationMs: 28_000, score: 7 },
        ],
      },
      {
        // A commit that `git revert` undid later: it is still on the branch.
        id: "c4",
        kind: "commit",
        title: "feat: filtros del canal en el servidor",
        author: "renzo",
        sha: "b52e9a0",
        ref: "main",
        url: "https://github.com/RenzoRamosDEV/Duelo/commit/b52e9a0",
        createdAt: minutesAgo(90),
        diff: DIFF,
        commitState: "reverted",
        revertedBy: { id: "c5", sha: "d93f0b4" },
        reviewStatus: "completed",
        reviews: [
          { id: "r7", agent: "claude", status: "completed", run: 1, durationMs: 40_000, score: 8 },
          { id: "r8", agent: "codex", status: "completed", run: 1, durationMs: 36_000, score: 9 },
        ],
      },
      {
        id: "c5",
        kind: "commit",
        title: 'Revert "feat: filtros del canal en el servidor"',
        author: "renzo",
        sha: "d93f0b4",
        ref: "main",
        url: "https://github.com/RenzoRamosDEV/Duelo/commit/d93f0b4",
        createdAt: minutesAgo(60),
        diff: DIFF,
        commitState: "active",
        reviewStatus: "completed",
        reviews: [
          { id: "r9", agent: "claude", status: "completed", run: 1, durationMs: 22_000, score: 7 },
          { id: "r10", agent: "codex", status: "completed", run: 1, durationMs: 19_000, score: 7 },
        ],
      },
      {
        id: "c2",
        kind: "pr",
        title: "feat: exponer ingesta de commits",
        author: "renzo",
        sha: "9be03d1",
        ref: "feat/ingest-commits",
        url: "https://github.com/RenzoRamosDEV/Duelo/pull/7",
        createdAt: minutesAgo(3 * 60),
        diff: DIFF,
        truncated: true,
        reviews: [
          {
            id: "r3",
            agent: "claude",
            status: "completed",
            run: 1,
            durationMs: 38_000,
            score: 7,
            summary: "Buen aislamiento de puertos; revisar idempotencia.",
            findings: [
              {
                severity: "high",
                file: "src/ingest.py",
                line: 3,
                message: "Idempotency-Key no se valida en longitud.",
              },
            ],
          },
          {
            id: "r4",
            agent: "codex",
            status: "failed",
            run: 1,
            durationMs: 120_000,
            error: "Tiempo de espera agotado al llamar al modelo.",
          },
        ],
      },
    ],
  },
  { slug: "acme/widgets", name: "acme/widgets", changes: [] },
];

export const agentStats: AgentStat[] = [
  {
    agent: "claude",
    total: 12,
    completed: 11,
    failed: 1,
    avgDurationMs: 42_000,
    avgScore: 4.1,
  },
  {
    agent: "codex",
    total: 10,
    completed: 7,
    failed: 3,
    avgDurationMs: 35_000,
    avgScore: 3.8,
  },
];

export const health: Health = {
  status: "ok",
  dependencies: [
    { name: "postgres", status: "ok", latencyMs: 4 },
    { name: "temporal", status: "ok", latencyMs: 12 },
  ],
  agentNames: ["claude", "codex"],
};

export function findProject(slug: string | undefined): Project | undefined {
  return projects.find((p) => p.slug === slug);
}

export function findChange(project: Project | undefined, id: string | undefined) {
  return project?.changes.find((c) => c.id === id);
}

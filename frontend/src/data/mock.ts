// View model shared by the UI, plus sample data used when no API is configured (VITE_API_URL).

export type AgentName = "claude" | "codex";
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
};

export function findProject(slug: string | undefined): Project | undefined {
  return projects.find((p) => p.slug === slug);
}

export function findChange(project: Project | undefined, id: string | undefined) {
  return project?.changes.find((c) => c.id === id);
}

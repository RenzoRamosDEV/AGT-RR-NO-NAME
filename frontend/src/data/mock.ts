// View model shared by the UI, plus sample data used when no API is configured (VITE_API_URL).

export type AgentName = "claude" | "codex";
export type ReviewStatus = "running" | "completed" | "failed";
export type ChangeKind = "commit" | "pr";

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
  diff: string;
  truncated?: boolean;
  /** Absent when the source does not report reviews (the API channel listing). */
  reviews?: Review[];
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
        diff: DIFF,
        reviews: [
          {
            id: "r1",
            agent: "claude",
            status: "completed",
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
        diff: DIFF,
        truncated: true,
        reviews: [
          {
            id: "r3",
            agent: "claude",
            status: "completed",
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
          { id: "r4", agent: "codex", status: "failed" },
        ],
      },
    ],
  },
  { slug: "demo-api", name: "demo-api", changes: [] },
];

export const stats = [
  { agent: "claude" as const, prompt: "v1", useful: 68, score: 4.1, seconds: 42, failures: 1 },
  { agent: "codex" as const, prompt: "v1", useful: 61, score: 3.8, seconds: 35, failures: 3 },
];

export function findProject(slug: string | undefined): Project | undefined {
  return projects.find((p) => p.slug === slug);
}

export function findChange(project: Project | undefined, id: string | undefined) {
  return project?.changes.find((c) => c.id === id);
}

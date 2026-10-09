// Sample data until the read API exists (Fase 4); types mirror the expected contract.

export type AgentName = "claude" | "codex";
export type ReviewStatus = "running" | "completed" | "failed";
export type ChangeKind = "commit" | "pr";

export interface Review {
  agent: AgentName;
  status: ReviewStatus;
  summary?: string;
  findings?: string[];
}

export interface Change {
  id: string;
  kind: ChangeKind;
  title: string;
  author: string;
  sha: string;
  diff: string;
  reviews: Review[];
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
    slug: "review-arena",
    name: "review-arena",
    changes: [
      {
        id: "c1",
        kind: "commit",
        title: "fix: comparar el token de ingesta en tiempo constante",
        author: "renzo",
        sha: "a41f9c2",
        diff: DIFF,
        reviews: [
          {
            agent: "claude",
            status: "completed",
            summary: "Cambio correcto; elimina la comparación vulnerable a timing.",
            findings: ["Falta test para token vacío.", "Considerar rotación del token."],
          },
          { agent: "codex", status: "running" },
        ],
      },
      {
        id: "c2",
        kind: "pr",
        title: "feat: exponer ingesta de commits",
        author: "renzo",
        sha: "9be03d1",
        diff: DIFF,
        reviews: [
          {
            agent: "claude",
            status: "completed",
            summary: "Buen aislamiento de puertos; revisar idempotencia.",
            findings: ["Idempotency-Key no se valida en longitud."],
          },
          { agent: "codex", status: "failed" },
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

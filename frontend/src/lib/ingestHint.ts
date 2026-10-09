export const DEFAULT_API_URL = "http://localhost:8000";

/**
 * Minimal `curl` to ingest a commit into `slug`. The token is always the `$INGEST_TOKEN`
 * placeholder: the UI must never print a real secret.
 */
export function ingestCommand(slug: string, apiUrl: string | undefined): string {
  const base = (apiUrl || DEFAULT_API_URL).replace(/\/+$/, "");
  // Only the required fields of `POST /ingest/commit`; title, author, url and diff are optional.
  const body = JSON.stringify({ project: slug, ref: "main", head_sha: "<sha del commit>" });
  return [
    `curl -X POST ${base}/ingest/commit`,
    `-H "Content-Type: application/json"`,
    `-H "X-Ingest-Token: $INGEST_TOKEN"`,
    `-d '${body.replaceAll("'", "'\\''")}'`,
  ].join(" \\\n  ");
}

/** Returns the URL only if it is http(s); change URLs come from ingestion and are untrusted. */
export function safeHttpUrl(value: string): string | null {
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : null;
  } catch {
    return null;
  }
}

export function shortSha(sha: string): string {
  return sha.slice(0, 7);
}

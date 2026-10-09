const MAX_LENGTH = 200;
const HIDDEN = "[oculto]";

// biome-ignore lint/suspicious/noControlCharactersInRegex: stripping control characters is the point
const CONTROL = /[\u0000-\u001f\u007f-\u009f]+/g;
const SECRET_PAIR = /\b(token|secret|password|passwd|api[_-]?key|authorization)(\s*[=:]\s*)\S+/gi;
const BEARER = /\bBearer\s+\S+/gi;
const KEY_LIKE = /\bsk-[A-Za-z0-9_-]{8,}/g;

/**
 * Makes a server-provided failure reason safe to show: no control characters, collapsed
 * whitespace, secret-looking values hidden and a bounded length. Returns `null` when nothing
 * readable is left.
 */
export function sanitizeError(text: string | null | undefined, max = MAX_LENGTH): string | null {
  if (!text) return null;
  const clean = text
    .replace(CONTROL, " ")
    .replace(SECRET_PAIR, `$1$2${HIDDEN}`)
    .replace(BEARER, `Bearer ${HIDDEN}`)
    .replace(KEY_LIKE, HIDDEN)
    .replace(/\s+/g, " ")
    .trim();
  if (!clean) return null;
  return clean.length > max ? `${clean.slice(0, max - 1).trimEnd()}…` : clean;
}

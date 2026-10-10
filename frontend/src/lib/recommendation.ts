/** Labels agents put in front of the advice at the end of a finding, lower case. */
const LABELS = [
  "arreglo",
  "sugerencia",
  "recomendación",
  "recomendacion",
  "recommendation",
  "suggestion",
  "fix",
];

/** What can come right before a label for it to start a sentence (or the text). */
const SENTENCE_END = ".!?;)\n";

export interface SplitMessage {
  /** The finding itself, without the advice. */
  body: string;
  /** The advice after a label such as `Arreglo:`, when the text carries one. */
  recommendation: string | undefined;
}

/** The index where `label:` (optionally `**label:**`) starts a sentence, or -1. */
function labelAt(lower: string, label: string): number {
  let from = 0;
  for (;;) {
    const at = lower.indexOf(label, from);
    if (at === -1) return -1;
    from = at + label.length;

    let end = at + label.length;
    while (lower[end] === "*" || lower[end] === " ") end += 1;
    if (lower[end] !== ":") continue;

    // The label must open a sentence: skip spaces and asterisks (`**Arreglo:**`) backwards.
    let before = at - 1;
    while (before >= 0 && (lower[before] === " " || lower[before] === "*")) before -= 1;
    if (before < 0 || SENTENCE_END.includes(lower[before] as string)) return at;
  }
}

/**
 * Separates `... problema. Arreglo: haz esto` into the problem and the advice. Without a label
 * the whole text is the body. The first label wins when there are several.
 */
export function splitRecommendation(message: string): SplitMessage {
  const lower = message.toLowerCase();
  let best = -1;
  let bestLabel = "";
  for (const label of LABELS) {
    const at = labelAt(lower, label);
    if (at !== -1 && (best === -1 || at < best)) {
      best = at;
      bestLabel = label;
    }
  }
  if (best === -1) return { body: message.trim(), recommendation: undefined };

  let start = best + bestLabel.length;
  while (message[start] === "*" || message[start] === " ") start += 1;
  start += 1; // The colon.
  const recommendation = message
    .slice(start)
    .replace(/^[\s*]+/, "")
    .trim();
  return {
    body: message
      .slice(0, best)
      .replace(/[\s*]+$/, "")
      .trim(),
    recommendation: recommendation || undefined,
  };
}

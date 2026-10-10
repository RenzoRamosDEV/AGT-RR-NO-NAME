import type { AgentName, Finding, Review } from "../data/mock";

export interface GroupedFinding extends Finding {
  agent: AgentName;
  key: string;
}

export interface FindingGroup {
  /** `undefined` groups the findings the agent could not locate in a file. */
  file: string | undefined;
  findings: GroupedFinding[];
}

/** From most to least serious; includes the backend's own words (`bug`, `risk`, `improvement`, `nit`). */
const SEVERITY_ORDER = [
  "critical",
  "bug",
  "high",
  "risk",
  "medium",
  "improvement",
  "low",
  "info",
  "nit",
];

/** Unknown severities (free text in the backend) sort after the known ones. */
export function severityRank(severity: string): number {
  const rank = SEVERITY_ORDER.indexOf(severity.toLowerCase());
  return rank === -1 ? SEVERITY_ORDER.length : rank;
}

const DANGER = new Set(["critical", "bug", "high"]);
const WARNING = new Set(["risk", "medium"]);

/** Color family of a severity: red for what breaks, amber for what may, neutral for the rest. */
export function severityTone(severity: string): "danger" | "warning" | "neutral" {
  const name = severity.toLowerCase();
  if (DANGER.has(name)) return "danger";
  return WARNING.has(name) ? "warning" : "neutral";
}

export type SeverityLevel = "danger" | "warning" | "info" | "neutral";

const INFO = new Set(["improvement", "low", "info"]);

/**
 * Four color families: red for what breaks, amber for what may, blue for improvements and gray for
 * nits (and for anything the agent invented).
 */
export function severityLevel(severity: string): SeverityLevel {
  const name = severity.toLowerCase();
  if (DANGER.has(name)) return "danger";
  if (WARNING.has(name)) return "warning";
  return INFO.has(name) ? "info" : "neutral";
}

const SEVERITY_LABEL: Record<string, string> = {
  critical: "Crítico",
  bug: "Bug",
  high: "Alto",
  risk: "Riesgo",
  medium: "Medio",
  improvement: "Mejora",
  low: "Bajo",
  info: "Info",
  nit: "Detalle",
};

/** Spanish name of a severity; an unknown one is shown as the agent wrote it, capitalized. */
export function severityLabel(severity: string): string {
  const name = severity.trim();
  return (
    SEVERITY_LABEL[name.toLowerCase()] ??
    (name ? name.charAt(0).toUpperCase() + name.slice(1) : "—")
  );
}

/** The backend (and some agents) send `N/A` or an empty string when there is no file. */
export function findingFile(finding: Pick<Finding, "file">): string | undefined {
  const file = finding.file?.trim();
  return !file || file.toUpperCase() === "N/A" ? undefined : file;
}

/** A line is only shown when it is a positive integer (`0` means unknown). */
export function findingLine(finding: Pick<Finding, "line">): number | undefined {
  return Number.isInteger(finding.line) && finding.line > 0 ? finding.line : undefined;
}

/** `file:line`, `file` or nothing, depending on what the finding actually carries. */
export function findingLocation(finding: Finding): string | undefined {
  const file = findingFile(finding);
  if (!file) return undefined;
  const line = findingLine(finding);
  return line ? `${file}:${line}` : file;
}

/**
 * Groups findings of all reviews by file; most severe first, then by line (unlocated last).
 * Files go alphabetically and the group without a file always comes last.
 */
export function groupFindings(reviews: Review[]): FindingGroup[] {
  const byFile = new Map<string | undefined, GroupedFinding[]>();
  for (const review of reviews) {
    (review.findings ?? []).forEach((finding, index) => {
      const file = findingFile(finding);
      const list = byFile.get(file) ?? [];
      list.push({ ...finding, agent: review.agent, key: `${review.id}-${index}` });
      byFile.set(file, list);
    });
  }
  return [...byFile.entries()]
    .map(([file, findings]) => ({
      file,
      findings: findings.sort(
        (a, b) =>
          severityRank(a.severity) - severityRank(b.severity) ||
          (findingLine(a) ?? Number.POSITIVE_INFINITY) -
            (findingLine(b) ?? Number.POSITIVE_INFINITY),
      ),
    }))
    .sort((a, b) => {
      if (a.file === undefined || b.file === undefined) {
        return Number(a.file === undefined) - Number(b.file === undefined);
      }
      return a.file.localeCompare(b.file);
    });
}

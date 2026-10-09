import type { AgentName, Finding, Review } from "../data/mock";

export interface GroupedFinding extends Finding {
  agent: AgentName;
  key: string;
}

export interface FindingGroup {
  file: string;
  findings: GroupedFinding[];
}

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

/** Unknown severities (free text in the backend) sort after the known ones. */
export function severityRank(severity: string): number {
  const rank = SEVERITY_ORDER.indexOf(severity.toLowerCase());
  return rank === -1 ? SEVERITY_ORDER.length : rank;
}

/** Groups findings of all reviews by file; most severe first, then by line. */
export function groupFindings(reviews: Review[]): FindingGroup[] {
  const byFile = new Map<string, GroupedFinding[]>();
  for (const review of reviews) {
    (review.findings ?? []).forEach((finding, index) => {
      const list = byFile.get(finding.file) ?? [];
      list.push({ ...finding, agent: review.agent, key: `${review.id}-${index}` });
      byFile.set(finding.file, list);
    });
  }
  return [...byFile.entries()]
    .map(([file, findings]) => ({
      file,
      findings: findings.sort(
        (a, b) => severityRank(a.severity) - severityRank(b.severity) || a.line - b.line,
      ),
    }))
    .sort((a, b) => a.file.localeCompare(b.file));
}

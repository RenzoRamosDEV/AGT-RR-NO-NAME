import { useMemo, useState } from "react";
import { FindingCard } from "../../components/FindingCard";
import type { Review } from "../../data/mock";
import { groupFindings, severityLabel, severityLevel, severityRank } from "../../lib/findings";

/** How many findings there are of each severity, most serious first. */
function severityCounts(reviews: Review[]): { severity: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const review of reviews) {
    for (const finding of review.findings ?? []) {
      const name = finding.severity.toLowerCase();
      counts.set(name, (counts.get(name) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .map(([severity, count]) => ({ severity, count }))
    .sort((a, b) => severityRank(a.severity) - severityRank(b.severity));
}

/**
 * Findings of every review as cards grouped by file, with a count per severity that also filters.
 * With none, it renders nothing: each review's card already says «Sin hallazgos».
 */
export function FindingsPanel({ reviews }: { reviews: Review[] }) {
  const [filter, setFilter] = useState<string | null>(null);
  const counts = useMemo(() => severityCounts(reviews), [reviews]);
  const groups = useMemo(() => groupFindings(reviews), [reviews]);
  const total = counts.reduce((sum, c) => sum + c.count, 0);

  if (total === 0) return null;

  // A filter whose severity disappeared (a refresh dropped it) must not leave the panel empty.
  const active = filter !== null && counts.some((c) => c.severity === filter) ? filter : null;
  const visible = groups
    .map((group) => ({
      ...group,
      findings: group.findings.filter(
        (f) => active === null || f.severity.toLowerCase() === active,
      ),
    }))
    .filter((group) => group.findings.length > 0);

  return (
    <section className="findings" aria-labelledby="findings-title">
      <div className="findings-head">
        <div className="findings-title">
          <h2 id="findings-title">Hallazgos</h2>
          <span className="count" aria-label={`${total} en total`}>
            {total}
          </span>
        </div>
        <fieldset className="severity-filter">
          <legend className="sr-only">Filtrar hallazgos por severidad</legend>
          <button
            type="button"
            className="sev-filter"
            data-level="all"
            aria-pressed={active === null}
            onClick={() => setFilter(null)}
          >
            Todos <span className="count">{total}</span>
          </button>
          {counts.map(({ severity, count }) => (
            <button
              key={severity}
              type="button"
              className="sev-filter"
              data-level={severityLevel(severity)}
              aria-pressed={active === severity}
              onClick={() => setFilter(active === severity ? null : severity)}
            >
              {severityLabel(severity)} <span className="count">{count}</span>
            </button>
          ))}
        </fieldset>
      </div>
      {visible.map((group) => (
        <div key={group.file ?? "no-file"} className="finding-group">
          <h3 className={group.file ? "mono" : undefined}>{group.file ?? "Sin archivo"}</h3>
          <ul className="finding-list">
            {group.findings.map((f) => (
              <li key={f.key}>
                <FindingCard id={f.key} finding={f} agent={f.agent} showFile={false} />
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}

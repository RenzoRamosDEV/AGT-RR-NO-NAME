import { agentLabel } from "../../components/ui/AgentAvatar";
import { Badge } from "../../components/ui/Badge";
import type { Review } from "../../data/mock";
import { findingLine, groupFindings, severityRank } from "../../lib/findings";

function tone(severity: string): "danger" | "warning" | "neutral" {
  const rank = severityRank(severity);
  if (rank <= 1) return "danger";
  return rank === 2 ? "warning" : "neutral";
}

/** Findings of every review grouped by file; renders nothing when there are none. */
export function FindingsPanel({ reviews }: { reviews: Review[] }) {
  const groups = groupFindings(reviews);
  if (groups.length === 0) return null;
  return (
    <section className="findings" aria-labelledby="findings-title">
      <h2 id="findings-title">Hallazgos</h2>
      {groups.map((group) => (
        <div key={group.file ?? "no-file"} className="finding-group">
          <h3 className={group.file ? "mono" : undefined}>{group.file ?? "Sin archivo"}</h3>
          <ul>
            {group.findings.map((f) => {
              const line = findingLine(f);
              return (
                <li key={f.key}>
                  <Badge tone={tone(f.severity)}>{f.severity}</Badge>{" "}
                  {line !== undefined && <span className="mono muted">L{line} </span>}
                  {f.message} <span className="muted">· {agentLabel(f.agent)}</span>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </section>
  );
}

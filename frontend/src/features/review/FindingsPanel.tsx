import { agentLabel } from "../../components/ui/AgentAvatar";
import { Badge } from "../../components/ui/Badge";
import type { Review } from "../../data/mock";
import { groupFindings, severityRank } from "../../lib/findings";

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
        <div key={group.file} className="finding-group">
          <h3 className="mono">{group.file}</h3>
          <ul>
            {group.findings.map((f) => (
              <li key={f.key}>
                <Badge tone={tone(f.severity)}>{f.severity}</Badge>{" "}
                <span className="mono muted">L{f.line}</span> {f.message}{" "}
                <span className="muted">· {agentLabel(f.agent)}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}

import { useState } from "react";
import { agentLabel } from "../../components/ui/AgentAvatar";
import { stats } from "../../data/mock";
import { ratio } from "../../lib/meter";
import { type SortDirection, nextSort, sortRows } from "../../lib/sort";

type Row = (typeof stats)[number];
type SortKey = keyof Row;
interface Sort {
  key: SortKey;
  direction: SortDirection;
}

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "agent", label: "Agente" },
  { key: "prompt", label: "Prompt" },
  { key: "useful", label: "% útiles" },
  { key: "score", label: "Nota" },
  { key: "seconds", label: "Duración" },
  { key: "failures", label: "Fallos" },
];

function Meter({ percent, tone }: { percent: number; tone?: "danger" }) {
  return (
    <span className="meter" aria-hidden="true" data-tone={tone}>
      <span style={{ width: `${percent}%` }} />
    </span>
  );
}

export function StatsPage() {
  const maxSeconds = Math.max(...stats.map((s) => s.seconds));
  const maxFailures = Math.max(...stats.map((s) => s.failures));
  const [sort, setSort] = useState<Sort | null>(null);
  const rows = sort ? sortRows(stats, sort.key, sort.direction) : stats;
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Estadísticas</h1>
          <p>Comparativa por agente y versión de prompt (datos de ejemplo).</p>
        </div>
      </div>
      <table className="stats">
        <thead>
          <tr>
            {COLUMNS.map((c) => (
              <th
                key={c.key}
                scope="col"
                aria-sort={sort?.key === c.key ? sort.direction : undefined}
              >
                <button
                  type="button"
                  className="sort-button"
                  onClick={() => setSort((current) => nextSort(current, c.key))}
                >
                  {c.label}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((s) => (
            <tr key={s.agent}>
              <th scope="row">{agentLabel(s.agent)}</th>
              <td className="mono">{s.prompt}</td>
              <td>
                {s.useful}%
                <Meter percent={ratio(s.useful, 100)} />
              </td>
              <td>{s.score.toFixed(1)}</td>
              <td>
                {s.seconds}s
                <Meter percent={ratio(s.seconds, maxSeconds)} />
              </td>
              <td>
                {s.failures}
                <Meter percent={ratio(s.failures, maxFailures)} tone="danger" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

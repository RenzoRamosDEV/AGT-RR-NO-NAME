import { useCallback, useState } from "react";
import { AsyncBoundary } from "../../components/AsyncBoundary";
import { EmptyState } from "../../components/EmptyState";
import { agentLabel } from "../../components/ui/AgentAvatar";
import type { AgentStat } from "../../data/mock";
import { useDataSource } from "../../data/source";
import { formatDuration, formatScore } from "../../lib/format";
import { ratio } from "../../lib/meter";
import { type SortDirection, nextSort, sortRows } from "../../lib/sort";
import { useAsync } from "../../lib/useAsync";

type SortKey = keyof AgentStat;
interface Sort {
  key: SortKey;
  direction: SortDirection;
}

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "agent", label: "Agente" },
  { key: "total", label: "Total" },
  { key: "completed", label: "Completadas" },
  { key: "failed", label: "Fallos" },
  { key: "avgDurationMs", label: "Duración media" },
  { key: "avgScore", label: "Nota media" },
];

function Meter({ percent, tone }: { percent: number; tone?: "danger" }) {
  return (
    <span className="meter" aria-hidden="true" data-tone={tone}>
      <span style={{ width: `${percent}%` }} />
    </span>
  );
}

function StatsTable({ stats }: { stats: AgentStat[] }) {
  const maxDuration = Math.max(0, ...stats.map((s) => s.avgDurationMs ?? 0));
  const maxFailures = Math.max(0, ...stats.map((s) => s.failed));
  const [sort, setSort] = useState<Sort | null>(null);
  const rows = sort ? sortRows(stats, sort.key, sort.direction) : stats;
  return (
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
            <td>{s.total}</td>
            <td>{s.completed}</td>
            <td>
              {s.failed}
              <Meter percent={ratio(s.failed, maxFailures)} tone="danger" />
            </td>
            <td>
              {formatDuration(s.avgDurationMs)}
              {s.avgDurationMs !== null && <Meter percent={ratio(s.avgDurationMs, maxDuration)} />}
            </td>
            <td>{formatScore(s.avgScore)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Mean of a per-agent average, weighted by how many reviews each agent has; null if none. */
function weightedMean(stats: AgentStat[], pick: (s: AgentStat) => number | null): number | null {
  let sum = 0;
  let weight = 0;
  for (const s of stats) {
    const value = pick(s);
    if (value === null) continue;
    sum += value * s.total;
    weight += s.total;
  }
  return weight > 0 ? sum / weight : null;
}

/** Insights-style cards above the table: the totals across every agent. */
function SummaryCards({ stats }: { stats: AgentStat[] }) {
  const total = stats.reduce((n, s) => n + s.total, 0);
  const completed = stats.reduce((n, s) => n + s.completed, 0);
  const failed = stats.reduce((n, s) => n + s.failed, 0);
  const items = [
    { label: "Reviews totales", value: String(total), tone: undefined },
    { label: "Completadas", value: String(completed), tone: "success" },
    { label: "Con fallo", value: String(failed), tone: failed > 0 ? "danger" : undefined },
    {
      label: "Duración media",
      value: formatDuration(weightedMean(stats, (s) => s.avgDurationMs)),
      tone: undefined,
    },
    {
      label: "Nota media",
      value: formatScore(weightedMean(stats, (s) => s.avgScore)),
      tone: undefined,
    },
  ];
  return (
    <dl className="stat-cards" aria-label="Resumen global">
      {items.map((item) => (
        <div key={item.label} className="stat-card" data-tone={item.tone}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function StatsPage() {
  const source = useDataSource();
  const state = useAsync(useCallback(() => source.agentStats(), [source]));
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Estadísticas</h1>
          <p>Reviews por agente: volumen, fallos y medias de duración y nota.</p>
        </div>
      </div>
      <AsyncBoundary state={state} loadingLabel="Cargando estadísticas…">
        {(stats) =>
          stats.length === 0 ? (
            <EmptyState title="Aún no hay reviews registradas.">
              <p className="muted">
                Cuando los agentes entreguen su primera review aparecerá aquí.
              </p>
            </EmptyState>
          ) : (
            <>
              <SummaryCards stats={stats} />
              <StatsTable stats={stats} />
            </>
          )
        }
      </AsyncBoundary>
    </div>
  );
}

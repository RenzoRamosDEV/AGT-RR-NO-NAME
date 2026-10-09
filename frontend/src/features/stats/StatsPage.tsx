import { agentLabel } from "../../components/ui/AgentAvatar";
import { stats } from "../../data/mock";
import { ratio } from "../../lib/meter";

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
            <th scope="col">Agente</th>
            <th scope="col">Prompt</th>
            <th scope="col">% útiles</th>
            <th scope="col">Nota</th>
            <th scope="col">Duración</th>
            <th scope="col">Fallos</th>
          </tr>
        </thead>
        <tbody>
          {stats.map((s) => (
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

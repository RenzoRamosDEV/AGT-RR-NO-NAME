import { agentLabel } from "../../components/ui/AgentAvatar";
import { stats } from "../../data/mock";

export function StatsPage() {
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
              <td>{s.useful}%</td>
              <td>{s.score.toFixed(1)}</td>
              <td>{s.seconds}s</td>
              <td>{s.failures}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

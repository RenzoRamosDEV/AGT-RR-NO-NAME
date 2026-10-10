import { useCallback } from "react";
import { AsyncBoundary } from "../../components/AsyncBoundary";
import { ThemeSwitch } from "../../components/ThemeSwitch";
import { AgentAvatar, agentLabel } from "../../components/ui/AgentAvatar";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import type { DependencyHealth, Health } from "../../data/mock";
import { useDataSource } from "../../data/source";
import { useAsync } from "../../lib/useAsync";
import { ProjectsSettings } from "./ProjectsSettings";

const DEPENDENCY_LABEL: Record<string, string> = { postgres: "Postgres", temporal: "Temporal" };
const REASON_LABEL: Record<NonNullable<DependencyHealth["reason"]>, string> = {
  timeout: "Tiempo agotado",
  error: "Error",
};

const dependencyLabel = (name: string) => DEPENDENCY_LABEL[name] ?? name;

/** The configured agents as chips with their avatar; a server that does not report them shows a dash. */
function AgentChips({ names }: { names: readonly string[] }) {
  if (names.length === 0) return <span className="muted">—</span>;
  return (
    <ul className="agent-chips" aria-label="Agentes activos">
      {names.map((name) => (
        <li key={name}>
          <AgentAvatar agent={name} size={20} />
          {agentLabel(name)}
        </li>
      ))}
    </ul>
  );
}

function Diagnostics({ health }: { health: Health }) {
  return (
    <>
      <div className="setting">
        <span>Estado del servidor</span>
        <Badge tone={health.status === "ok" ? "success" : "warning"}>
          {health.status === "ok" ? "Correcto" : "Degradado"}
        </Badge>
      </div>
      {health.dependencies.map((d) => (
        <div className="setting" key={d.name}>
          <span>{dependencyLabel(d.name)}</span>
          <span className="row">
            <Badge tone={d.status === "ok" ? "success" : "danger"}>
              {d.status === "ok" ? "Disponible" : "No disponible"}
            </Badge>
            <span className="muted">{d.latencyMs} ms</span>
            {d.reason && <span className="muted">{REASON_LABEL[d.reason]}</span>}
          </span>
        </div>
      ))}
    </>
  );
}

export function SettingsPage() {
  const source = useDataSource();
  const health = useAsync(useCallback(() => source.health(), [source]));
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Ajustes</h1>
          <p>Apariencia, estado del servidor y proyectos vigilados.</p>
        </div>
      </div>
      <section className="box" aria-labelledby="settings-appearance">
        <h2 className="box-title" id="settings-appearance">
          Apariencia
        </h2>
        <div className="setting">
          <span>
            Tema
            <span className="setting-hint muted">
              «Sistema» sigue la preferencia de tu sistema operativo.
            </span>
          </span>
          <ThemeSwitch />
        </div>
      </section>
      <section className="box" aria-labelledby="settings-general">
        <h2 className="box-title" id="settings-general">
          General
        </h2>
        <div className="setting">
          <span>Voto ciego</span>
          <Badge>Próximamente</Badge>
        </div>
        <div className="setting">
          <span>Agentes activos</span>
          {health.status === "ready" ? (
            <AgentChips names={health.data.agentNames} />
          ) : (
            <span className="muted">—</span>
          )}
        </div>
      </section>
      <ProjectsSettings />
      <section className="box" aria-labelledby="settings-health">
        <div className="box-title row">
          <h2 id="settings-health">Diagnóstico</h2>
          <Button size="sm" onClick={health.retry}>
            Actualizar
          </Button>
        </div>
        <AsyncBoundary state={health} loadingLabel="Comprobando dependencias…" activity="connect">
          {(data) => <Diagnostics health={data} />}
        </AsyncBoundary>
      </section>
    </div>
  );
}

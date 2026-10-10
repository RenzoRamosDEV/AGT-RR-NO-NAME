import { useCallback } from "react";
import { AsyncBoundary } from "../../components/AsyncBoundary";
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
          <p>Estado del servidor y proyectos vigilados; el resto aún no se persiste.</p>
        </div>
      </div>
      <div className="setting">
        <span>Voto ciego</span>
        <Badge>Próximamente</Badge>
      </div>
      <div className="setting">
        <span>Agentes activos</span>
        <span className="muted">Claude, Codex</span>
      </div>
      <ProjectsSettings />
      <section aria-labelledby="settings-health">
        <div className="row">
          <h2 id="settings-health">Diagnóstico</h2>
          <Button onClick={health.retry}>Actualizar</Button>
        </div>
        <AsyncBoundary state={health} loadingLabel="Comprobando dependencias…">
          {(data) => <Diagnostics health={data} />}
        </AsyncBoundary>
      </section>
    </div>
  );
}

import { Badge } from "../../components/ui/Badge";
import { projects } from "../../data/mock";

export function SettingsPage() {
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Ajustes</h1>
          <p>Configuración de ejemplo; aún no se persiste.</p>
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
      <div className="setting">
        <span>Proyectos vigilados</span>
        <span className="muted">{projects.map((p) => p.name).join(", ")}</span>
      </div>
    </div>
  );
}

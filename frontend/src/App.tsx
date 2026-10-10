import { Link, Navigate, Route, Routes, useParams } from "react-router";
import { AsyncBoundary } from "./components/AsyncBoundary";
import { Button } from "./components/ui/Button";
import { ChannelPage } from "./features/channel/ChannelPage";
import { useProjects } from "./features/projects/ProjectsContext";
import { ChangeDetailPage } from "./features/review/ChangeDetailPage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { StatsPage } from "./features/stats/StatsPage";
import { Shell } from "./layout/Shell";
import { parseProjectPath, projectPath } from "./lib/projectPath";

function FirstProject() {
  const { projects, openAddProject } = useProjects();
  return (
    <div className="page">
      <AsyncBoundary state={projects} loadingLabel="Cargando proyectos…">
        {(list) =>
          list.length > 0 ? (
            <Navigate to={projectPath(list[0].slug)} replace />
          ) : (
            <div className="stack">
              <p className="muted">Aún no hay proyectos vigilados.</p>
              <div className="actions">
                <Button variant="primary" onClick={openAddProject}>
                  Añadir proyecto
                </Button>
              </div>
            </div>
          )
        }
      </AsyncBoundary>
    </div>
  );
}

function NotFoundPage() {
  return (
    <div className="page">
      <h1>No encontrado</h1>
      <p className="muted">Esta dirección no corresponde a ninguna página.</p>
      <Link to="/">Volver al inicio</Link>
    </div>
  );
}

/** `p/*`: the slug can contain "/", so the route is parsed by hand (see `lib/projectPath`). */
function ProjectRoute() {
  const route = parseProjectPath(useParams()["*"]);
  if (route.kind === "channel") return <ChannelPage key={route.slug} slug={route.slug} />;
  if (route.kind === "change") return <ChangeDetailPage slug={route.slug} id={route.id} />;
  return <NotFoundPage />;
}

function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<FirstProject />} />
        <Route path="p/*" element={<ProjectRoute />} />
        <Route path="stats" element={<StatsPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

export default App;

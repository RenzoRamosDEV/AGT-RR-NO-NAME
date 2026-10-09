import { useCallback } from "react";
import { Link, Navigate, Route, Routes, useParams } from "react-router";
import { AsyncBoundary } from "./components/AsyncBoundary";
import { useDataSource } from "./data/source";
import { ChannelPage } from "./features/channel/ChannelPage";
import { ChangeDetailPage } from "./features/review/ChangeDetailPage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { StatsPage } from "./features/stats/StatsPage";
import { Shell } from "./layout/Shell";
import { parseProjectPath, projectPath } from "./lib/projectPath";
import { useAsync } from "./lib/useAsync";

function FirstProject() {
  const source = useDataSource();
  const state = useAsync(useCallback(() => source.projects(), [source]));
  return (
    <div className="page">
      <AsyncBoundary state={state} loadingLabel="Cargando proyectos…">
        {(projects) =>
          projects.length > 0 ? (
            <Navigate to={projectPath(projects[0].slug)} replace />
          ) : (
            <p className="muted">Aún no hay proyectos vigilados.</p>
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

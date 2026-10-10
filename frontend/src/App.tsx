import { Link, Navigate, Route, Routes, useParams } from "react-router";
import { AsyncBoundary } from "./components/AsyncBoundary";
import { EmptyState } from "./components/EmptyState";
import { UpdatePrompt } from "./components/UpdatePrompt";
import { HERO } from "./components/brand";
import { MetalButton } from "./components/fx/MetalButton";
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
            <EmptyState
              hero={HERO}
              title="Aún no hay proyectos vigilados."
              action={
                <MetalButton variant="primary" onClick={openAddProject}>
                  Añadir proyecto
                </MetalButton>
              }
            >
              <p className="muted">
                Añade la carpeta de un repositorio git y Duelo revisará cada commit y push.
              </p>
            </EmptyState>
          )
        }
      </AsyncBoundary>
    </div>
  );
}

function NotFoundPage() {
  return (
    <div className="page">
      <EmptyState
        kind="missing"
        hero={HERO}
        heading
        title="No encontrado"
        action={
          <Link className="btn btn-primary" to="/">
            Volver al inicio
          </Link>
        }
      >
        <p className="muted">Esta dirección no corresponde a ninguna página.</p>
      </EmptyState>
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
    <>
      <Routes>
        <Route element={<Shell />}>
          <Route index element={<FirstProject />} />
          <Route path="p/*" element={<ProjectRoute />} />
          <Route path="stats" element={<StatsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
      {/* The service worker only exists in the production build; dev and tests never register it. */}
      {import.meta.env.PROD && <UpdatePrompt />}
    </>
  );
}

export default App;

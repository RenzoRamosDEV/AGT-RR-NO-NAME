import { useEffect, useId, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router";
import { Button } from "../components/ui/Button";
import { ProjectsProvider, useProjects } from "../features/projects/ProjectsContext";
import { projectPath } from "../lib/projectPath";

const link = ({ isActive }: { isActive: boolean }) => (isActive ? "nav-link active" : "nav-link");

export function Shell() {
  return (
    <ProjectsProvider>
      <ShellLayout />
    </ProjectsProvider>
  );
}

function ShellLayout() {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const { pathname } = useLocation();
  const { projects, openAddProject } = useProjects();

  // biome-ignore lint/correctness/useExhaustiveDependencies: close the menu whenever the route changes
  useEffect(() => setOpen(false), [pathname]);

  return (
    <div className="shell">
      <nav
        className="sidebar"
        aria-label="Principal"
        data-open={open}
        onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
      >
        <div className="sidebar-head">
          <div className="brand">Duelo</div>
          <Button
            className="menu-toggle"
            aria-expanded={open}
            aria-controls={panelId}
            onClick={() => setOpen((o) => !o)}
          >
            Menú
          </Button>
        </div>
        <div className="nav-panel" id={panelId}>
          <div className="nav-group">
            <div className="nav-title">Proyectos</div>
            {projects.status === "loading" && <output className="muted">Cargando…</output>}
            {projects.status === "error" && (
              <div role="alert">
                <p className="muted">No se pudieron cargar los proyectos.</p>
                <Button onClick={projects.retry}>Reintentar</Button>
              </div>
            )}
            {projects.status === "ready" &&
              (projects.data.length === 0 ? (
                <p className="muted">Sin proyectos.</p>
              ) : (
                projects.data.map((p) => (
                  <NavLink key={p.slug} to={projectPath(p.slug)} className={link}>
                    <span aria-hidden="true">#</span> {p.name}
                  </NavLink>
                ))
              ))}
            <Button onClick={openAddProject}>Añadir proyecto</Button>
          </div>
          <div className="nav-group">
            <div className="nav-title">General</div>
            <NavLink to="/stats" className={link}>
              Estadísticas
            </NavLink>
            <NavLink to="/settings" className={link}>
              Ajustes
            </NavLink>
          </div>
        </div>
      </nav>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}

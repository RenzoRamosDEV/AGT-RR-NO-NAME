import { useEffect, useId, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router";
import { BrandLogo } from "../components/BrandLogo";
import { Busy } from "../components/Busy";
import { ThemeSwitch } from "../components/ThemeSwitch";
import { ChartIcon, ChevronIcon, GearIcon, MenuIcon, PlusIcon } from "../components/icons";
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
  const [channelsOpen, setChannelsOpen] = useState(true);
  const panelId = useId();
  const channelsId = useId();
  const { pathname } = useLocation();
  const { projects, openAddProject } = useProjects();

  // biome-ignore lint/correctness/useExhaustiveDependencies: close the menu whenever the route changes
  useEffect(() => setOpen(false), [pathname]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="app">
      <header className="topbar">
        <Button
          variant="ghost"
          className="menu-toggle"
          aria-label="Menú"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((o) => !o)}
        >
          <MenuIcon />
        </Button>
        <Link to="/" className="brand">
          <BrandLogo size={28} />
          <span>Duelo</span>
        </Link>
        <div className="topbar-spacer" />
        <ThemeSwitch compact />
      </header>
      <div className="shell">
        <nav
          className="sidebar"
          aria-label="Principal"
          data-open={open}
          onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
        >
          <div className="nav-panel" id={panelId}>
            <div className="nav-group">
              <button
                type="button"
                className="nav-title"
                aria-expanded={channelsOpen}
                aria-controls={channelsId}
                onClick={() => setChannelsOpen((o) => !o)}
              >
                <ChevronIcon className="nav-chevron" size={12} />
                Proyectos
              </button>
              <div id={channelsId} hidden={!channelsOpen}>
                {projects.status === "loading" && <Busy activity="load" label="Cargando…" />}
                {projects.status === "error" && (
                  <div role="alert" className="nav-note">
                    <p className="muted">No se pudieron cargar los proyectos.</p>
                    <Button size="sm" onClick={projects.retry}>
                      Reintentar
                    </Button>
                  </div>
                )}
                {projects.status === "ready" &&
                  (projects.data.length === 0 ? (
                    <p className="muted nav-note">Sin proyectos.</p>
                  ) : (
                    projects.data.map((p) => (
                      <NavLink key={p.slug} to={projectPath(p.slug)} className={link}>
                        <span className="hash" aria-hidden="true">
                          #
                        </span>{" "}
                        {p.name}
                      </NavLink>
                    ))
                  ))}
                <button type="button" className="nav-add" onClick={openAddProject}>
                  <PlusIcon />
                  <span>Añadir proyecto</span>
                </button>
              </div>
            </div>
            <div className="nav-group">
              <div className="nav-title static">General</div>
              <NavLink to="/stats" className={link}>
                <ChartIcon />
                Estadísticas
              </NavLink>
              <NavLink to="/settings" className={link}>
                <GearIcon />
                Ajustes
              </NavLink>
            </div>
          </div>
        </nav>
        <main className="main">
          <Outlet />
        </main>
      </div>
      {open && (
        <button
          type="button"
          className="scrim"
          aria-label="Cerrar el menú"
          tabIndex={-1}
          onClick={() => setOpen(false)}
        />
      )}
    </div>
  );
}

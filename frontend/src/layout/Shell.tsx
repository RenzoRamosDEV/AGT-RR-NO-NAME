import { useEffect, useId, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router";
import { Button } from "../components/ui/Button";
import { projects } from "../data/mock";

const link = ({ isActive }: { isActive: boolean }) => (isActive ? "nav-link active" : "nav-link");

export function Shell() {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const { pathname } = useLocation();

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
            {projects.map((p) => (
              <NavLink key={p.slug} to={`/p/${p.slug}`} className={link}>
                <span aria-hidden="true">#</span> {p.name}
              </NavLink>
            ))}
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

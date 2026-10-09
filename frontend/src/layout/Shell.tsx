import { NavLink, Outlet } from "react-router";
import { projects } from "../data/mock";

const link = ({ isActive }: { isActive: boolean }) => (isActive ? "nav-link active" : "nav-link");

export function Shell() {
  return (
    <div className="shell">
      <nav className="sidebar" aria-label="Principal">
        <div className="brand">Duelo</div>
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
      </nav>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}

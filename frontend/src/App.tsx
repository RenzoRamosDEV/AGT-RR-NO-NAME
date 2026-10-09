import { useCallback } from "react";
import { Navigate, Route, Routes } from "react-router";
import { AsyncBoundary } from "./components/AsyncBoundary";
import { useDataSource } from "./data/source";
import { ChannelPage } from "./features/channel/ChannelPage";
import { ChangeDetailPage } from "./features/review/ChangeDetailPage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { StatsPage } from "./features/stats/StatsPage";
import { Shell } from "./layout/Shell";
import { useAsync } from "./lib/useAsync";

function FirstProject() {
  const source = useDataSource();
  const state = useAsync(useCallback(() => source.projects(), [source]));
  return (
    <div className="page">
      <AsyncBoundary state={state} loadingLabel="Cargando proyectos…">
        {(projects) =>
          projects.length > 0 ? (
            <Navigate to={`/p/${projects[0].slug}`} replace />
          ) : (
            <p className="muted">Aún no hay proyectos vigilados.</p>
          )
        }
      </AsyncBoundary>
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<FirstProject />} />
        <Route path="p/:slug" element={<ChannelPage />} />
        <Route path="p/:slug/changes/:id" element={<ChangeDetailPage />} />
        <Route path="stats" element={<StatsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}

export default App;

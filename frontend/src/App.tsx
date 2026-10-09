import { Navigate, Route, Routes } from "react-router";
import { projects } from "./data/mock";
import { ChannelPage } from "./features/channel/ChannelPage";
import { ChangeDetailPage } from "./features/review/ChangeDetailPage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { StatsPage } from "./features/stats/StatsPage";
import { Shell } from "./layout/Shell";

function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Navigate to={`/p/${projects[0].slug}`} replace />} />
        <Route path="p/:slug" element={<ChannelPage />} />
        <Route path="p/:slug/changes/:id" element={<ChangeDetailPage />} />
        <Route path="stats" element={<StatsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}

export default App;

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import "./index.css";
import App from "./App.tsx";
import { NowProvider } from "./lib/now";
import { PollingProvider } from "./lib/polling";
import { applyTheme } from "./lib/theme";

// The inline script in index.html already set it before first paint; this keeps it in sync with
// the system when the preference is "system".
applyTheme();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <NowProvider>
        <PollingProvider>
          <App />
        </PollingProvider>
      </NowProvider>
    </BrowserRouter>
  </StrictMode>,
);

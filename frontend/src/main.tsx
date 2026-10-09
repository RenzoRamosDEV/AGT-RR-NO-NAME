import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import "./index.css";
import App from "./App.tsx";
import { NowProvider } from "./lib/now";
import { PollingProvider } from "./lib/polling";

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

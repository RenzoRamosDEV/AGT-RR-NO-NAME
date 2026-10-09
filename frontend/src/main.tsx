import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import "./index.css";
import App from "./App.tsx";
import { NowProvider } from "./lib/now";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <NowProvider>
        <App />
      </NowProvider>
    </BrowserRouter>
  </StrictMode>,
);

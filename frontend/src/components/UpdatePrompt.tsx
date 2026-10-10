import { useRegisterSW } from "virtual:pwa-register/react";
import { Button } from "./ui/Button";

/**
 * Tells the user a new build is waiting and lets them reload when they want. The service worker
 * never reloads the page by itself (`registerType: "prompt"`), so a review is never cut mid-read.
 */
export function UpdatePrompt() {
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW();
  if (!needRefresh) return null;
  return (
    // `<output>` carries the implicit "status" role, so screen readers announce the new version.
    <output className="update-prompt">
      <p>Nueva versión disponible.</p>
      <Button variant="primary" size="sm" onClick={() => updateServiceWorker(true)}>
        Actualizar
      </Button>
      <Button variant="ghost" size="sm" onClick={() => setNeedRefresh(false)}>
        Cerrar
      </Button>
    </output>
  );
}

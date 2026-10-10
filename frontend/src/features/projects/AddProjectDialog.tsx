import { type FormEvent, useId, useState } from "react";
import { Modal } from "../../components/Modal";
import { Button } from "../../components/ui/Button";
import { useDataSource } from "../../data/source";
import { ApiError, type ProjectRef } from "../../lib/api";
import { clearIngestToken, useIngestToken } from "../../lib/ingestToken";
import { isAbsolutePath } from "../../lib/localPath";

interface Props {
  onClose: () => void;
  onAdded: (project: ProjectRef) => void;
}

function failureMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "Ocurrió un error inesperado.";
  switch (error.status) {
    case 404:
      return "Esta función está desactivada en la API: arranca con LOCAL_PROJECTS_ENABLED=true.";
    case 409:
      return "Este proyecto ya está añadido.";
    case 422:
      return "La ruta no es un repositorio git válido. Comprueba que existe y que contiene una carpeta .git.";
    case 401:
      return "Token de ingesta no válido.";
    case null:
      return error.message;
    default:
      return `No se pudo añadir el proyecto: ${error.message}`;
  }
}

/** Asks for the absolute path of a local git repository and registers it through the API. */
export function AddProjectDialog({ onClose, onAdded }: Props) {
  const source = useDataSource();
  const [token, setToken] = useIngestToken();
  const [path, setPath] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pathId = useId();
  const tokenId = useId();
  const hintId = useId();

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (sending) return;
    const value = path.trim();
    if (!isAbsolutePath(value)) {
      setError(
        "Escribe la ruta absoluta del repositorio (empieza por / o por una unidad como C:\\).",
      );
      return;
    }
    if (!token.trim()) {
      setError("Introduce el token de ingesta.");
      return;
    }
    setSending(true);
    setError(null);
    try {
      onAdded(await source.addProject(value, token.trim()));
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) clearIngestToken();
      setError(failureMessage(e));
      setSending(false);
    }
  }

  return (
    <Modal title="Añadir proyecto" onClose={onClose}>
      <form className="modal-form" onSubmit={submit}>
        <p className="muted" id={hintId}>
          Al añadirlo, Duelo instalará dos hooks de git en ese repositorio (<code>post-commit</code>{" "}
          y <code>pre-push</code>) para recibir cada commit y push. Se desinstalan quitando el
          proyecto en Ajustes.
        </p>
        <label htmlFor={pathId}>Ruta del repositorio</label>
        <input
          id={pathId}
          className="search"
          type="text"
          autoComplete="off"
          spellCheck={false}
          placeholder="/home/usuario/proyectos/mi-repo"
          aria-describedby={hintId}
          data-autofocus
          value={path}
          onChange={(e) => setPath(e.target.value)}
        />
        <label htmlFor={tokenId}>Token de ingesta</label>
        <input
          id={tokenId}
          className="search"
          type="password"
          autoComplete="off"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        {error && (
          <p className="notice" role="alert">
            {error}
          </p>
        )}
        <div className="modal-actions">
          <Button onClick={onClose}>Cancelar</Button>
          <Button type="submit" variant="primary" disabled={sending}>
            {sending ? "Añadiendo…" : "Añadir"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

import { type FormEvent, useId, useState } from "react";
import { AsyncBoundary } from "../../components/AsyncBoundary";
import { Busy } from "../../components/Busy";
import { Modal } from "../../components/Modal";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { useDataSource } from "../../data/source";
import { ApiError, type ProjectRef } from "../../lib/api";
import { clearIngestToken, useIngestToken } from "../../lib/ingestToken";
import { useProjects } from "../projects/ProjectsContext";

interface Message {
  tone: "ok" | "error";
  text: string;
}

const MISSING_TOKEN = "Introduce el token de ingesta.";

function failureMessage(error: unknown, action: string): string {
  if (!(error instanceof ApiError)) return "Ocurrió un error inesperado.";
  switch (error.status) {
    case 401:
      return "Token de ingesta no válido.";
    case 404:
      return "El proyecto ya no existe.";
    case null:
      return error.message;
    default:
      return `No se pudo ${action}: ${error.message}`;
  }
}

function syncText({ synced, created }: { synced: number; created: number }): string {
  const prs = `${synced} ${synced === 1 ? "PR sincronizada" : "PRs sincronizadas"}`;
  return `${prs} (${created} ${created === 1 ? "nueva" : "nuevas"}).`;
}

function TokenField({ id }: { id: string }) {
  const [token, setToken] = useIngestToken();
  return (
    <>
      <label htmlFor={id}>Token de ingesta</label>
      <input
        id={id}
        className="search"
        type="password"
        autoComplete="off"
        value={token}
        onChange={(e) => setToken(e.target.value)}
      />
    </>
  );
}

function RemoveDialog({
  project,
  onClose,
  onRemoved,
}: {
  project: ProjectRef;
  onClose: () => void;
  onRemoved: () => void;
}) {
  const source = useDataSource();
  const [token] = useIngestToken();
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const tokenId = useId();

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (sending) return;
    if (!token.trim()) {
      setError(MISSING_TOKEN);
      return;
    }
    setSending(true);
    setError(null);
    try {
      await source.removeProject(project.slug, token.trim());
      onRemoved();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) clearIngestToken();
      // 409: no se pudieron quitar los hooks y el proyecto se conserva. El servidor dice qué
      // revisar (permisos de .git/hooks), así que su mensaje se muestra tal cual.
      setError(
        e instanceof ApiError && e.status === 409
          ? `${e.message} El proyecto se conserva: puedes repetir la baja.`
          : failureMessage(e, "quitar el proyecto"),
      );
      setSending(false);
    }
  }

  return (
    <Modal title={`Quitar ${project.name}`} onClose={onClose}>
      <form className="modal-form" onSubmit={submit}>
        <p>
          Se borrará <strong>todo el historial</strong> de este proyecto en Duelo (changes, reviews
          y eventos)
          {project.hooksInstalled ? " y se desinstalarán sus hooks de git" : ""}. Los archivos de tu
          repositorio no se tocan. Esta acción no se puede deshacer.
        </p>
        <TokenField id={tokenId} />
        {error && (
          <p className="notice" role="alert">
            {error}
          </p>
        )}
        <div className="modal-actions">
          <Button onClick={onClose} data-autofocus>
            Cancelar
          </Button>
          <Button type="submit" variant="danger" disabled={sending}>
            {sending ? <Busy activity="connect" label="Quitando…" inline /> : "Quitar proyecto"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ProjectRow({
  project,
  message,
  syncing,
  onSync,
  onRemove,
}: {
  project: ProjectRef;
  message: Message | undefined;
  syncing: boolean;
  onSync: () => void;
  onRemove: () => void;
}) {
  return (
    <li className="project-row">
      <div>
        <strong>{project.name}</strong>
        {project.path && <div className="mono muted">{project.path}</div>}
      </div>
      <div className="row">
        {project.hooksInstalled !== undefined && (
          <Badge tone={project.hooksInstalled ? "success" : "warning"}>
            {project.hooksInstalled ? "Hooks instalados" : "Sin hooks"}
          </Badge>
        )}
        {project.github && (
          <Button
            size="sm"
            onClick={onSync}
            disabled={syncing}
            aria-busy={syncing}
            // While it runs the visible text is the name ("Sincronizando…"): a fixed aria-label
            // would hide it from assistive technology.
            aria-label={syncing ? undefined : `Sincronizar PRs de ${project.name}`}
          >
            {syncing ? (
              <Busy activity="connect" label="Sincronizando…" inline />
            ) : (
              "Sincronizar PRs"
            )}
          </Button>
        )}
        <Button
          variant="danger"
          size="sm"
          onClick={onRemove}
          aria-label={`Quitar proyecto ${project.name}`}
        >
          Quitar proyecto
        </Button>
      </div>
      {message &&
        (message.tone === "error" ? (
          <p className="notice project-message" role="alert">
            {message.text}
          </p>
        ) : (
          <output className="notice project-message">{message.text}</output>
        ))}
    </li>
  );
}

/** Settings section: the live list of projects with their path and hooks, sync and removal. */
export function ProjectsSettings() {
  const source = useDataSource();
  const { projects, openAddProject } = useProjects();
  const [token] = useIngestToken();
  const [messages, setMessages] = useState<Record<string, Message>>({});
  const [syncing, setSyncing] = useState<string | null>(null);
  const [removing, setRemoving] = useState<ProjectRef | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const tokenId = useId();

  const say = (slug: string, message: Message) =>
    setMessages((current) => ({ ...current, [slug]: message }));

  async function sync(project: ProjectRef) {
    if (syncing) return;
    if (!token.trim()) {
      say(project.slug, { tone: "error", text: MISSING_TOKEN });
      return;
    }
    setSyncing(project.slug);
    try {
      say(project.slug, {
        tone: "ok",
        text: syncText(await source.syncPrs(project.slug, token.trim())),
      });
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) clearIngestToken();
      say(project.slug, { tone: "error", text: failureMessage(e, "sincronizar las PRs") });
    } finally {
      setSyncing(null);
    }
  }

  return (
    <section className="box" aria-labelledby="settings-projects">
      <div className="box-title row">
        <h2 id="settings-projects">Proyectos vigilados</h2>
        <Button size="sm" variant="primary" onClick={openAddProject}>
          Añadir proyecto
        </Button>
      </div>
      {notice && <output className="notice flat success">{notice}</output>}
      <AsyncBoundary state={projects} loadingLabel="Cargando proyectos…">
        {(list) =>
          list.length === 0 ? (
            <p className="muted box-pad">Aún no hay proyectos vigilados.</p>
          ) : (
            <>
              <div className="retry">
                <TokenField id={tokenId} />
              </div>
              <ul className="plain-list">
                {list.map((p) => (
                  <ProjectRow
                    key={p.slug}
                    project={p}
                    message={messages[p.slug]}
                    syncing={syncing === p.slug}
                    onSync={() => sync(p)}
                    onRemove={() => setRemoving(p)}
                  />
                ))}
              </ul>
            </>
          )
        }
      </AsyncBoundary>
      {removing && (
        <RemoveDialog
          project={removing}
          onClose={() => setRemoving(null)}
          onRemoved={() => {
            setNotice(`Proyecto ${removing.name} quitado.`);
            setRemoving(null);
            projects.refresh();
          }}
        />
      )}
    </section>
  );
}

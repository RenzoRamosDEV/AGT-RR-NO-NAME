import { useId, useState } from "react";
import { Link, useParams } from "react-router";
import { AsyncBoundary } from "../../components/AsyncBoundary";
import { CopyButton } from "../../components/CopyButton";
import { ReviewCard } from "../../components/ReviewCard";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import type { Change, ChangeKind } from "../../data/mock";
import { ApiError } from "../../lib/api";
import { type StateFilter, matchesState } from "../../lib/changeFilters";
import { ingestCommand } from "../../lib/ingestHint";
import { useNow } from "../../lib/now";
import { relativeTime } from "../../lib/relativeTime";
import { summarizeReviews } from "../../lib/reviewSummary";
import { matchesQuery } from "../../lib/search";
import { shortSha } from "../../lib/url";
import { useChannel } from "./useChannel";

type Filter = "all" | ChangeKind;

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "Todo" },
  { value: "pr", label: "PRs" },
  { value: "commit", label: "Commits" },
];

const STATE_FILTERS: { value: StateFilter; label: string }[] = [
  { value: "all", label: "Todos" },
  { value: "running", label: "En curso" },
  { value: "failed", label: "Con fallos" },
  { value: "completed", label: "Completados" },
];

type Density = "cards" | "compact";

const DENSITIES: { value: Density; label: string }[] = [
  { value: "cards", label: "Tarjetas" },
  { value: "compact", label: "Compacta" },
];

function Age({ iso }: { iso: string | undefined }) {
  const now = useNow();
  const text = iso ? relativeTime(iso, now) : null;
  if (!iso || !text) return null;
  return (
    <time dateTime={iso} title={new Date(iso).toLocaleString("es-ES")}>
      {text}
    </time>
  );
}

function ChangeThread({
  change,
  slug,
  compact,
}: {
  change: Change;
  slug: string;
  compact: boolean;
}) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  return (
    <Card className={compact ? "change-row" : undefined}>
      <div className="row">
        <Badge>{change.kind === "pr" ? "PR" : "Commit"}</Badge>
        <Link to={`/p/${slug}/changes/${change.id}`}>
          <strong>{change.title}</strong>
        </Link>
      </div>
      <p className="muted">
        {change.author} · <span className="mono">{shortSha(change.sha)}</span>
        {change.createdAt && (
          <>
            {" · "}
            <Age iso={change.createdAt} />
          </>
        )}
      </p>
      <ul className="review-summary" aria-label="Resumen de reviews">
        {summarizeReviews(change.reviews ?? []).map((item) => (
          <li key={item.status}>
            <Badge
              tone={
                item.status === "completed"
                  ? "success"
                  : item.status === "failed"
                    ? "danger"
                    : "neutral"
              }
            >
              {item.text}
            </Badge>
          </li>
        ))}
      </ul>
      <Button aria-expanded={open} aria-controls={panelId} onClick={() => setOpen((o) => !o)}>
        {open ? "Ocultar respuestas" : "Ver respuestas"}
      </Button>
      {open && (
        <div className="thread reviews" id={panelId}>
          {(change.reviews ?? []).map((r) => (
            <ReviewCard key={r.id} review={r} />
          ))}
        </div>
      )}
    </Card>
  );
}

function EmptyChannel({ slug }: { slug: string }) {
  const command = ingestCommand(slug, import.meta.env.VITE_API_URL);
  return (
    <Card className="empty">
      <p>
        <strong>Aún no hay cambios en este canal.</strong>
      </p>
      <p className="muted">
        Envía un commit a la API para que Claude y Codex lo revisen. Sustituye{" "}
        <code>$INGEST_TOKEN</code> por el token de ingesta configurado en el servidor.
      </p>
      <pre className="command">
        <code>{command}</code>
      </pre>
      <CopyButton label="Copiar comando" value={command} />
    </Card>
  );
}

export function ChannelPage() {
  const { slug = "" } = useParams();
  const [filter, setFilter] = useState<Filter>("all");
  const [stateFilter, setStateFilter] = useState<StateFilter>("all");
  const [query, setQuery] = useState("");
  const [density, setDensity] = useState<Density>("cards");
  const searchId = useId();
  const { first, items, hasMore, moreState, loadMore } = useChannel(
    slug,
    filter === "all" ? undefined : filter,
  );

  if (first.status === "error" && first.error instanceof ApiError && first.error.notFound) {
    return (
      <div className="page">
        <h1>Proyecto no encontrado</h1>
      </div>
    );
  }

  const changes = items.filter((c) => matchesState(c, stateFilter) && matchesQuery(c, query));
  const emptyChannel = items.length === 0 && filter === "all" && !hasMore;
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>#{slug}</h1>
          <p>Commits y PRs revisados por Claude y Codex.</p>
        </div>
      </div>
      <div className="toolbar">
        <label className="visually-hidden" htmlFor={searchId}>
          Buscar cambios
        </label>
        <input
          id={searchId}
          className="search"
          type="search"
          placeholder="Buscar por título, autor o SHA"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <fieldset className="filters" aria-label="Filtro">
          {FILTERS.map((f) => (
            <Button
              key={f.value}
              aria-pressed={filter === f.value}
              onClick={() => setFilter(f.value)}
            >
              {f.label}
            </Button>
          ))}
        </fieldset>
        <fieldset className="filters" aria-label="Densidad">
          {DENSITIES.map((d) => (
            <Button
              key={d.value}
              aria-pressed={density === d.value}
              onClick={() => setDensity(d.value)}
            >
              {d.label}
            </Button>
          ))}
        </fieldset>
        <fieldset className="filters" aria-label="Estado de la review">
          {STATE_FILTERS.map((f) => (
            <Button
              key={f.value}
              aria-pressed={stateFilter === f.value}
              onClick={() => setStateFilter(f.value)}
            >
              {f.label}
            </Button>
          ))}
        </fieldset>
      </div>
      <div className="stack">
        <AsyncBoundary state={first} loadingLabel="Cargando cambios…">
          {() => (
            <>
              {changes.length === 0 && !emptyChannel && (
                <output className="muted">Ningún cambio coincide con la búsqueda.</output>
              )}
              {emptyChannel && <EmptyChannel slug={slug} />}
              {changes.map((c) => (
                <ChangeThread key={c.id} change={c} slug={slug} compact={density === "compact"} />
              ))}
              {moreState === "error" && (
                <p className="notice" role="alert">
                  No se pudieron cargar más cambios.
                </p>
              )}
              {hasMore && (
                <Button onClick={loadMore} disabled={moreState === "loading"}>
                  {moreState === "loading"
                    ? "Cargando…"
                    : moreState === "error"
                      ? "Reintentar"
                      : "Cargar más"}
                </Button>
              )}
            </>
          )}
        </AsyncBoundary>
      </div>
    </div>
  );
}

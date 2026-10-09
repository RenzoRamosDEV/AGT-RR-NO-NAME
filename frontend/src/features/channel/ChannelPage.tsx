import { useId, useState } from "react";
import { Link } from "react-router";
import { AsyncBoundary } from "../../components/AsyncBoundary";
import { CopyButton } from "../../components/CopyButton";
import { ReviewCard } from "../../components/ReviewCard";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import type { Change, ChangeKind } from "../../data/mock";
import { ApiError } from "../../lib/api";
import type { StateFilter } from "../../lib/channelQuery";
import { ingestCommand } from "../../lib/ingestHint";
import { useNow } from "../../lib/now";
import { changePath } from "../../lib/projectPath";
import { relativeTime } from "../../lib/relativeTime";
import { AGGREGATE_LABEL, AGGREGATE_TONE } from "../../lib/reviewStatus";
import { summarizeReviews } from "../../lib/reviewSummary";
import { shortSha } from "../../lib/url";
import { useDebouncedValue } from "../../lib/useDebouncedValue";
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

const SEARCH_DELAY_MS = 300;

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

type Tone = "neutral" | "success" | "danger" | "warning";

/** Per-review counts when the source brings the reviews, else the aggregate status. */
function summaryItems(change: Change): { key: string; tone: Tone; text: string }[] {
  if (change.reviews) {
    return summarizeReviews(change.reviews).map((item) => ({
      key: item.status,
      tone:
        item.status === "completed" ? "success" : item.status === "failed" ? "danger" : "neutral",
      text: item.text,
    }));
  }
  const status = change.reviewStatus;
  return status
    ? [{ key: status, tone: AGGREGATE_TONE[status], text: AGGREGATE_LABEL[status] }]
    : [];
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
        <Link to={changePath(slug, change.id)}>
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
        {summaryItems(change).map((item) => (
          <li key={item.key}>
            <Badge tone={item.tone}>{item.text}</Badge>
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

export function ChannelPage({ slug }: { slug: string }) {
  const [filter, setFilter] = useState<Filter>("all");
  const [stateFilter, setStateFilter] = useState<StateFilter>("all");
  const [query, setQuery] = useState("");
  const [density, setDensity] = useState<Density>("cards");
  const searchId = useId();
  const search = useDebouncedValue(query.trim(), SEARCH_DELAY_MS);
  const { first, items, hasMore, moreState, loadMore } = useChannel(slug, {
    kind: filter === "all" ? undefined : filter,
    state: stateFilter,
    q: search,
  });

  if (first.status === "error" && first.error instanceof ApiError && first.error.notFound) {
    return (
      <div className="page">
        <h1>Proyecto no encontrado</h1>
      </div>
    );
  }

  const unfiltered = filter === "all" && stateFilter === "all" && search === "";
  const emptyChannel = items.length === 0 && unfiltered && !hasMore;
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
          placeholder="Buscar por título, autor, SHA o rama"
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
              {items.length === 0 && !emptyChannel && (
                <output className="muted">Ningún cambio coincide con la búsqueda.</output>
              )}
              {emptyChannel && <EmptyChannel slug={slug} />}
              {items.map((c) => (
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

import { useId, useState } from "react";
import { Link, useParams } from "react-router";
import { ReviewCard } from "../../components/ReviewCard";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { type Change, type ChangeKind, findProject } from "../../data/mock";

type Filter = "all" | ChangeKind;

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "Todo" },
  { value: "pr", label: "PRs" },
  { value: "commit", label: "Commits" },
];

function ChangeThread({ change, slug }: { change: Change; slug: string }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  return (
    <Card>
      <div className="row">
        <Badge>{change.kind === "pr" ? "PR" : "Commit"}</Badge>
        <Link to={`/p/${slug}/changes/${change.id}`}>
          <strong>{change.title}</strong>
        </Link>
      </div>
      <p className="muted">
        {change.author} · <span className="mono">{change.sha}</span>
      </p>
      <Button aria-expanded={open} aria-controls={panelId} onClick={() => setOpen((o) => !o)}>
        {open ? "Ocultar respuestas" : "Ver respuestas"}
      </Button>
      {open && (
        <div className="thread reviews" id={panelId}>
          {change.reviews.map((r) => (
            <ReviewCard key={r.agent} review={r} />
          ))}
        </div>
      )}
    </Card>
  );
}

export function ChannelPage() {
  const { slug } = useParams();
  const project = findProject(slug);
  const [filter, setFilter] = useState<Filter>("all");

  if (!project || !slug) {
    return (
      <div className="page">
        <h1>Proyecto no encontrado</h1>
      </div>
    );
  }

  const changes = project.changes.filter((c) => filter === "all" || c.kind === filter);
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>#{project.name}</h1>
          <p>Commits y PRs revisados por Claude y Codex.</p>
        </div>
      </div>
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
      <div className="stack">
        {changes.length === 0 && <p className="muted">Aún no hay cambios en este canal.</p>}
        {changes.map((c) => (
          <ChangeThread key={c.id} change={c} slug={slug} />
        ))}
      </div>
    </div>
  );
}

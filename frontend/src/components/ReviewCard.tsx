import { BorderBeam } from "border-beam";
import type { Review, ReviewStatus } from "../data/mock";
import { findingLocation } from "../lib/findings";
import { formatDuration, formatScore } from "../lib/format";
import { sanitizeError } from "../lib/sanitize";
import { useReducedMotion } from "../lib/useReducedMotion";
import { AgentThinking } from "./AgentThinking";
import { AgentAvatar, agentLabel } from "./ui/AgentAvatar";
import { Badge } from "./ui/Badge";

const STATUS: Record<ReviewStatus, { text: string; tone: "neutral" | "success" | "danger" }> = {
  running: { text: "En curso", tone: "neutral" },
  completed: { text: "Completada", tone: "success" },
  failed: { text: "Fallida", tone: "danger" },
};

function Meta({ review }: { review: Review }) {
  const items = [
    review.run !== undefined && `Run ${review.run}`,
    review.durationMs != null && formatDuration(review.durationMs),
    review.score != null && `Nota ${formatScore(review.score)}`,
  ].filter((item): item is string => typeof item === "string");
  if (items.length === 0) return null;
  return (
    <ul className="review-meta" aria-label="Datos de la review">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function Body({ review }: { review: Review }) {
  const { text, tone } = STATUS[review.status];
  const name = agentLabel(review.agent);
  const reason = review.status === "failed" ? sanitizeError(review.error) : null;
  return (
    <div className="review-body">
      <div className="row">
        <AgentAvatar agent={review.agent} />
        <strong>{name}</strong>
        <Badge tone={tone}>{text}</Badge>
      </div>
      <Meta review={review} />
      {review.status === "running" && <AgentThinking label={`${name} está revisando…`} />}
      {review.status === "failed" && <p className="muted">La review no pudo completarse.</p>}
      {reason && <p className="review-error">Motivo: {reason}</p>}
      {review.status === "completed" && (
        <>
          <p>{review.summary}</p>
          <ul>
            {review.findings?.map((f) => {
              const location = findingLocation(f);
              return (
                <li key={`${f.file}:${f.line}:${f.message}`}>
                  {f.message}
                  {location && <span className="mono muted"> {location}</span>}
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}

export function ReviewCard({ review }: { review: Review }) {
  const reduced = useReducedMotion();
  if (review.status !== "running" || reduced) {
    return (
      <article className="review" data-status={review.status}>
        <Body review={review} />
      </article>
    );
  }
  return (
    <BorderBeam colorVariant="mono" size="md" className="review" data-status="running">
      <article>
        <Body review={review} />
      </article>
    </BorderBeam>
  );
}

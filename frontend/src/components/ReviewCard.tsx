import type { Review, ReviewStatus } from "../data/mock";
import { findingLocation, severityTone } from "../lib/findings";
import { formatDuration, formatScore } from "../lib/format";
import { sanitizeError } from "../lib/sanitize";
import { AgentThinking } from "./AgentThinking";
import { AgentAvatar, agentLabel } from "./ui/AgentAvatar";
import { Badge } from "./ui/Badge";

const STATUS: Record<ReviewStatus, { text: string; tone: "neutral" | "success" | "danger" }> = {
  running: { text: "En curso", tone: "neutral" },
  completed: { text: "Completada", tone: "success" },
  failed: { text: "Fallida", tone: "danger" },
};

/** The "reactions" under a message: run, duration and score as small pills. */
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

function Body({ review, showFindings }: { review: Review; showFindings: boolean }) {
  const { text, tone } = STATUS[review.status];
  const name = agentLabel(review.agent);
  const reason = review.status === "failed" ? sanitizeError(review.error) : null;
  return (
    <>
      <AgentAvatar agent={review.agent} />
      <div className="message-main">
        <div className="message-head">
          <strong className="message-author">{name}</strong>
          <span className="app-tag">APP</span>
          <Badge tone={tone}>{text}</Badge>
        </div>
        {review.status === "running" && <AgentThinking label={`${name} está revisando…`} />}
        {review.status === "failed" && <p className="muted">La review no pudo completarse.</p>}
        {reason && <p className="review-error">Motivo: {reason}</p>}
        {review.status === "completed" && !review.partial && (
          <>
            <p className="message-text">{review.summary}</p>
            {showFindings && review.findings && review.findings.length > 0 && (
              <ul className="message-findings">
                {review.findings.map((f) => {
                  const location = findingLocation(f);
                  return (
                    <li
                      key={`${f.file}:${f.line}:${f.message}`}
                      data-tone={severityTone(f.severity)}
                    >
                      {f.message}
                      {location && <span className="mono muted"> {location}</span>}
                    </li>
                  );
                })}
              </ul>
            )}
          </>
        )}
        <Meta review={review} />
      </div>
    </>
  );
}

/**
 * A review rendered like a Slack message from an app: avatar, author with an APP tag, body.
 * `showFindings` is off where a grouped findings panel already lists them (the change detail).
 */
export function ReviewCard({
  review,
  showFindings = true,
}: {
  review: Review;
  showFindings?: boolean;
}) {
  return (
    <article className="review message" data-status={review.status}>
      <Body review={review} showFindings={showFindings} />
    </article>
  );
}

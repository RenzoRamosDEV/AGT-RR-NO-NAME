import { BorderBeam } from "border-beam";
import type { Review, ReviewStatus } from "../data/mock";
import { useReducedMotion } from "../lib/useReducedMotion";
import { AgentThinking } from "./AgentThinking";
import { AgentAvatar, agentLabel } from "./ui/AgentAvatar";
import { Badge } from "./ui/Badge";

const STATUS: Record<ReviewStatus, { text: string; tone: "neutral" | "success" | "danger" }> = {
  running: { text: "En curso", tone: "neutral" },
  completed: { text: "Completada", tone: "success" },
  failed: { text: "Fallida", tone: "danger" },
};

function Body({ review }: { review: Review }) {
  const { text, tone } = STATUS[review.status];
  const name = agentLabel(review.agent);
  return (
    <div className="review-body">
      <div className="row">
        <AgentAvatar agent={review.agent} />
        <strong>{name}</strong>
        <Badge tone={tone}>{text}</Badge>
      </div>
      {review.status === "running" && <AgentThinking label={`${name} está revisando…`} />}
      {review.status === "failed" && <p className="muted">La review no pudo completarse.</p>}
      {review.status === "completed" && (
        <>
          <p>{review.summary}</p>
          <ul>
            {review.findings?.map((f) => (
              <li key={`${f.file}:${f.line}:${f.message}`}>
                {f.message}{" "}
                <span className="mono muted">
                  {f.file}:{f.line}
                </span>
              </li>
            ))}
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

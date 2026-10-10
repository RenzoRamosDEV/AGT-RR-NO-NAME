import type { Review, ReviewStatus } from "../data/mock";
import { findingFile, findingLine, severityRank } from "../lib/findings";
import { formatDuration, formatScore } from "../lib/format";
import { sanitizeError } from "../lib/sanitize";
import { AgentThinking } from "./AgentThinking";
import { Collapsible, SUMMARY_LIMIT, isLong } from "./Collapsible";
import { FindingCard } from "./FindingCard";
import { Markdown } from "./Markdown";
import { CheckCircleIcon } from "./icons";
import { AgentAvatar, agentHue, agentLabel } from "./ui/AgentAvatar";
import { Badge } from "./ui/Badge";

const STATUS: Record<ReviewStatus, { text: string; tone: "neutral" | "success" | "danger" }> = {
  running: { text: "En curso", tone: "neutral" },
  completed: { text: "Completada", tone: "success" },
  failed: { text: "Fallida", tone: "danger" },
};

/** The "reactions" of a message: run, duration and score as small pills. */
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

/** Most serious first, then by file and line, so the card reads from what matters most. */
function orderedFindings(review: Review) {
  return (review.findings ?? [])
    .map((finding, index) => ({ finding, key: `${review.id}-f${index}` }))
    .sort(
      (a, b) =>
        severityRank(a.finding.severity) - severityRank(b.finding.severity) ||
        (findingFile(a.finding) ?? "\uffff").localeCompare(findingFile(b.finding) ?? "\uffff") ||
        (findingLine(a.finding) ?? Number.POSITIVE_INFINITY) -
          (findingLine(b.finding) ?? Number.POSITIVE_INFINITY),
    );
}

function Completed({ review, showFindings }: { review: Review; showFindings: boolean }) {
  const findings = orderedFindings(review);
  const summary = review.summary?.trim();
  return (
    <>
      {summary && (
        <section className="review-section" aria-label="Resumen">
          <h4 className="section-label">Resumen</h4>
          <Collapsible id={`summary:${review.id}`} long={isLong(summary, SUMMARY_LIMIT)}>
            <Markdown text={summary} className="review-text" />
          </Collapsible>
        </section>
      )}
      {findings.length === 0 && (
        <p className="no-findings">
          <CheckCircleIcon size={14} />
          Sin hallazgos
        </p>
      )}
      {showFindings && findings.length > 0 && (
        <section className="review-section" aria-label="Hallazgos">
          <h4 className="section-label">
            Hallazgos <span className="count">{findings.length}</span>
          </h4>
          <ul className="finding-list">
            {findings.map(({ finding, key }) => (
              <li key={key}>
                <FindingCard id={key} finding={finding} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

function Body({ review, showFindings }: { review: Review; showFindings: boolean }) {
  const { text, tone } = STATUS[review.status];
  const name = agentLabel(review.agent);
  const reason = review.status === "failed" ? sanitizeError(review.error) : null;
  return (
    <>
      <AgentAvatar agent={review.agent} size={36} />
      <div className="message-main">
        <div className="message-head">
          <strong className="message-author">{name}</strong>
          <span className="app-tag">APP</span>
          <Badge tone={tone}>{text}</Badge>
          <Meta review={review} />
        </div>
        {review.status === "running" && <AgentThinking label={`${name} está revisando…`} />}
        {review.status === "failed" && (
          <div className="review-error-box">
            <p>La review no pudo completarse.</p>
            {reason && <p className="review-error">Motivo: {reason}</p>}
          </div>
        )}
        {review.status === "completed" && !review.partial && (
          <Completed review={review} showFindings={showFindings} />
        )}
      </div>
    </>
  );
}

/**
 * A review rendered like a Slack message from an app: avatar, author with an APP tag, status and
 * data on the header line, then the summary and the findings as cards. `showFindings` is off where
 * a grouped findings panel already lists them (the change detail).
 */
export function ReviewCard({
  review,
  showFindings = true,
}: {
  review: Review;
  showFindings?: boolean;
}) {
  return (
    <article
      className="review message"
      data-status={review.status}
      style={{ "--avatar-hue": agentHue(review.agent) } as React.CSSProperties}
    >
      <Body review={review} showFindings={showFindings} />
    </article>
  );
}

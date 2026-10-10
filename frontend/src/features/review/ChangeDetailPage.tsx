import { useCallback, useState } from "react";
import { Link } from "react-router";
import { AsyncBoundary } from "../../components/AsyncBoundary";
import { CopyButton } from "../../components/CopyButton";
import { EmptyState } from "../../components/EmptyState";
import { ReviewCard } from "../../components/ReviewCard";
import { StatusIcon } from "../../components/StatusIcon";
import { UndoneBanner } from "../../components/UndoneNotice";
import { UpdatedAgo } from "../../components/UpdatedAgo";
import { HERO } from "../../components/brand";
import { Beam } from "../../components/fx/Beam";
import { ExternalIcon, FileIcon } from "../../components/icons";
import type { Change, Review } from "../../data/mock";
import { useAgentNames, useDataSource } from "../../data/source";
import { UNNAMED_FILE, diffFiles, diffSquares, parseDiff } from "../../lib/diff";
import { sameValue } from "../../lib/equal";
import { usePollMs } from "../../lib/polling";
import { projectPath } from "../../lib/projectPath";
import { AGGREGATE_LABEL, AGGREGATE_TONE, isRetryable } from "../../lib/reviewStatus";
import { splitRuns } from "../../lib/runs";
import { safeHttpUrl, shortSha } from "../../lib/url";
import { useAsync } from "../../lib/useAsync";
import { FindingsPanel } from "./FindingsPanel";
import { PendingAgents } from "./PendingAgents";
import { RetryReview } from "./RetryReview";

const fileAnchor = (rowId: number) => `diff-file-${rowId}`;

/** A change whose reviews are still being produced keeps refreshing; a finished one does not. */
const inProgress = (change: Change) =>
  change.reviewStatus === "pending" || change.reviewStatus === "running";

/** Reviews in a stable order (by agent), whatever order the API sends them in. */
const byAgent = (reviews: Review[]) => [...reviews].sort((a, b) => a.agent.localeCompare(b.agent));

/** GitHub's bar of five squares next to a file's +N −M. */
function Squares({ additions, deletions }: { additions: number; deletions: number }) {
  const { add, del, neutral } = diffSquares(additions, deletions);
  const squares = [
    ...Array.from({ length: add }, () => "add"),
    ...Array.from({ length: del }, () => "del"),
    ...Array.from({ length: neutral }, () => "neutral"),
  ];
  return (
    <span className="squares" aria-hidden="true">
      {squares.map((kind, i) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: five fixed decorative squares
        <span key={i} data-kind={kind} />
      ))}
    </span>
  );
}

export function ChangeDetailPage({ slug, id }: { slug: string; id: string }) {
  const source = useDataSource();
  const agentNames = useAgentNames();
  const state = useAsync(
    useCallback(() => source.change(id), [source, id]),
    {
      pollMs: usePollMs(),
      pollWhile: inProgress,
      equals: (a: Change, b: Change) => sameValue(a, b),
    },
  );
  const [note, setNote] = useState<string | null>(null);
  const reload = state.retry;

  return (
    <AsyncBoundary
      state={state}
      loadingLabel="Cargando change…"
      notFound={
        <div className="page">
          <EmptyState kind="missing" hero={HERO} heading title="Change no encontrado">
            <p className="muted">Este change no existe o se eliminó junto con su proyecto.</p>
          </EmptyState>
        </div>
      }
    >
      {(change) => {
        const url = safeHttpUrl(change.url);
        // Only the current run counts; a retry keeps the earlier runs' reviews, shown collapsed.
        const { current: reviews, previous } = splitRuns(change.reviews ?? [], change.run);
        const rows = parseDiff(change.diff);
        const files = diffFiles(rows);
        const anchored = new Set(files.map((f) => f.rowId));
        const totalAdd = files.reduce((n, f) => n + f.additions, 0);
        const totalDel = files.reduce((n, f) => n + f.deletions, 0);
        return (
          <div className="page">
            <div className="detail-head">
              <p className="crumbs">
                <Link to={projectPath(slug)}>#{slug}</Link> /{" "}
                <span className="mono">{shortSha(change.sha)}</span>
              </p>
              <h1>{change.title}</h1>
              <UndoneBanner change={change} slug={slug} />
              {change.reviewStatus && (
                <p className="row status-line">
                  <span className="status-pill" data-tone={AGGREGATE_TONE[change.reviewStatus]}>
                    <StatusIcon status={change.reviewStatus} />
                    {AGGREGATE_LABEL[change.reviewStatus]}
                  </span>
                  {change.run !== undefined && <span className="muted">Run {change.run}</span>}
                  <span className="muted">
                    por {change.author}
                    {change.ref && (
                      <>
                        {" en "}
                        <span className="mono">{change.ref}</span>
                      </>
                    )}
                  </span>
                </p>
              )}
              <PendingAgents change={change} agentNames={agentNames} />
              {inProgress(change) && (
                <UpdatedAgo updatedAt={state.updatedAt} failed={state.refreshFailed} />
              )}
              <div className="actions">
                {url && (
                  <a className="btn" href={url} target="_blank" rel="noopener noreferrer">
                    Abrir en GitHub
                    <ExternalIcon size={14} />
                  </a>
                )}
                <CopyButton label="Copiar SHA" value={change.sha} />
                {change.ref && <CopyButton label="Copiar rama" value={change.ref} />}
              </div>
            </div>
            {note && (
              <output className="notice success" aria-live="polite">
                {note}
              </output>
            )}
            {isRetryable(change.reviewStatus) && (
              <RetryReview
                changeId={change.id}
                onSettled={(message) => {
                  setNote(message);
                  reload();
                }}
              />
            )}
            <div className="stack">
              <Beam active={inProgress(change)}>
                <section className="box" aria-labelledby="thread-title">
                  <h2 className="box-title" id="thread-title">
                    Revisión de los agentes
                  </h2>
                  <div className="box-body">
                    {reviews.length === 0 && !inProgress(change) && (
                      <p className="muted">Aún no hay respuestas de los agentes.</p>
                    )}
                    <div className="reviews">
                      {byAgent(reviews).map((r) => (
                        <ReviewCard key={r.id} review={r} showFindings={false} sha={change.sha} />
                      ))}
                    </div>
                    <FindingsPanel reviews={reviews} />
                    {previous.map((p) => (
                      <details key={p.run} className="previous-run">
                        <summary>
                          Run {p.run} (anterior) · {p.reviews.length}{" "}
                          {p.reviews.length === 1 ? "review" : "reviews"}
                        </summary>
                        <div className="reviews">
                          {byAgent(p.reviews).map((r) => (
                            <ReviewCard key={r.id} review={r} sha={change.sha} />
                          ))}
                        </div>
                      </details>
                    ))}
                  </div>
                </section>
              </Beam>
              <section className="box" aria-labelledby="files-title">
                <h2 className="box-title" id="files-title">
                  Archivos cambiados
                  {files.length > 0 && (
                    <span className="box-sub">
                      <span className="add-count">+{totalAdd}</span>{" "}
                      <span className="del-count">−{totalDel}</span>
                    </span>
                  )}
                </h2>
                {change.truncated && (
                  <p className="notice flat" role="note">
                    El diff está truncado: solo se muestra una parte de los cambios.
                  </p>
                )}
                {files.some((f) => f.name !== UNNAMED_FILE) && (
                  <nav className="diff-files" aria-label="Archivos del diff">
                    <h3>
                      {files.length} {files.length === 1 ? "archivo" : "archivos"}
                    </h3>
                    <ul>
                      {files.map((f) => (
                        <li key={f.rowId}>
                          <FileIcon size={14} />
                          <a href={`#${fileAnchor(f.rowId)}`} className="mono">
                            {f.name}
                          </a>{" "}
                          <span className="file-stat">
                            <span className="add-count">+{f.additions}</span>{" "}
                            <span className="del-count">−{f.deletions}</span>
                            <Squares additions={f.additions} deletions={f.deletions} />
                          </span>
                        </li>
                      ))}
                    </ul>
                  </nav>
                )}
                <div className="diff-scroll">
                  <table className="diff" aria-label="Diff">
                    <tbody>
                      {rows.map((row) => (
                        <tr
                          key={row.id}
                          id={anchored.has(row.id) ? fileAnchor(row.id) : undefined}
                          className={`diff-row ${row.kind}${row.kind === "header" ? (row.file ? " file" : " hunk") : ""}`}
                        >
                          <td className="ln" aria-hidden="true">
                            {row.oldNo ?? ""}
                          </td>
                          <td className="ln" aria-hidden="true">
                            {row.newNo ?? ""}
                          </td>
                          <td className="code">
                            {row.kind === "header" ? (
                              <strong>{row.file ?? row.text.replace(/^@@\s*/, "")}</strong>
                            ) : (
                              row.text
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          </div>
        );
      }}
    </AsyncBoundary>
  );
}

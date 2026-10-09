import { useCallback } from "react";
import { Link, useParams } from "react-router";
import { AsyncBoundary } from "../../components/AsyncBoundary";
import { CopyButton } from "../../components/CopyButton";
import { ReviewCard } from "../../components/ReviewCard";
import { useDataSource } from "../../data/source";
import { UNNAMED_FILE, diffFiles, parseDiff } from "../../lib/diff";
import { safeHttpUrl, shortSha } from "../../lib/url";
import { useAsync } from "../../lib/useAsync";
import { FindingsPanel } from "./FindingsPanel";

const fileAnchor = (rowId: number) => `diff-file-${rowId}`;

export function ChangeDetailPage() {
  const { slug = "", id = "" } = useParams();
  const source = useDataSource();
  const state = useAsync(useCallback(() => source.change(id), [source, id]));

  return (
    <AsyncBoundary
      state={state}
      loadingLabel="Cargando change…"
      notFound={
        <div className="page">
          <h1>Change no encontrado</h1>
        </div>
      }
    >
      {(change) => {
        const url = safeHttpUrl(change.url);
        const reviews = change.reviews ?? [];
        const rows = parseDiff(change.diff);
        const files = diffFiles(rows);
        const anchored = new Set(files.map((f) => f.rowId));
        return (
          <div className="page">
            <div className="page-header">
              <div>
                <p>
                  <Link to={`/p/${slug}`}>#{slug}</Link> /{" "}
                  <span className="mono">{shortSha(change.sha)}</span>
                </p>
                <h1>{change.title}</h1>
              </div>
            </div>
            <div className="actions">
              {url && (
                <a className="btn" href={url} target="_blank" rel="noopener noreferrer">
                  Abrir en GitHub
                </a>
              )}
              <CopyButton label="Copiar SHA" value={change.sha} />
              {change.ref && <CopyButton label="Copiar rama" value={change.ref} />}
            </div>
            <div className="stack">
              {change.truncated && (
                <p className="notice" role="note">
                  El diff está truncado: solo se muestra una parte de los cambios.
                </p>
              )}
              {files.some((f) => f.name !== UNNAMED_FILE) && (
                <nav className="diff-files" aria-label="Archivos del diff">
                  <h2>
                    {files.length} {files.length === 1 ? "archivo" : "archivos"}
                  </h2>
                  <ul>
                    {files.map((f) => (
                      <li key={f.rowId}>
                        <a href={`#${fileAnchor(f.rowId)}`} className="mono">
                          {f.name}
                        </a>{" "}
                        <span className="add-count">+{f.additions}</span>{" "}
                        <span className="del-count">−{f.deletions}</span>
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
                        className={`diff-row ${row.kind}`}
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
              <FindingsPanel reviews={reviews} />
              <div className="reviews">
                {reviews.map((r) => (
                  <ReviewCard key={r.id} review={r} />
                ))}
              </div>
            </div>
          </div>
        );
      }}
    </AsyncBoundary>
  );
}

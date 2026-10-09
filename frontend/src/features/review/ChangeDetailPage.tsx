import { useCallback } from "react";
import { Link, useParams } from "react-router";
import { AsyncBoundary } from "../../components/AsyncBoundary";
import { CopyButton } from "../../components/CopyButton";
import { ReviewCard } from "../../components/ReviewCard";
import { useDataSource } from "../../data/source";
import { parseDiff } from "../../lib/diff";
import { safeHttpUrl, shortSha } from "../../lib/url";
import { useAsync } from "../../lib/useAsync";
import { FindingsPanel } from "./FindingsPanel";

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
              <div className="diff-scroll">
                <table className="diff" aria-label="Diff">
                  <tbody>
                    {parseDiff(change.diff).map((row) => (
                      <tr key={row.id} className={`diff-row ${row.kind}`}>
                        <td className="ln" aria-hidden="true">
                          {row.oldNo ?? ""}
                        </td>
                        <td className="ln" aria-hidden="true">
                          {row.newNo ?? ""}
                        </td>
                        <td className="code">
                          {row.kind === "header" ? (
                            <strong>{row.text.replace(/^@@\s*/, "")}</strong>
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

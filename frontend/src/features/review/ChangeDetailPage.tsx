import { Link, useParams } from "react-router";
import { ReviewCard } from "../../components/ReviewCard";
import { findChange, findProject } from "../../data/mock";
import { parseDiff } from "../../lib/diff";

export function ChangeDetailPage() {
  const { slug, id } = useParams();
  const project = findProject(slug);
  const change = findChange(project, id);

  if (!project || !change) {
    return (
      <div className="page">
        <h1>Change no encontrado</h1>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <p>
            <Link to={`/p/${project.slug}`}>#{project.name}</Link> /{" "}
            <span className="mono">{change.sha}</span>
          </p>
          <h1>{change.title}</h1>
        </div>
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
        <div className="reviews">
          {change.reviews.map((r) => (
            <ReviewCard key={r.agent} review={r} />
          ))}
        </div>
      </div>
    </div>
  );
}

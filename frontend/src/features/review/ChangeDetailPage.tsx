import { Link, useParams } from "react-router";
import { ReviewCard } from "../../components/ReviewCard";
import { findChange, findProject } from "../../data/mock";

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
        <pre className="diff" aria-label="Diff">
          {change.diff.split("\n").map((line) => (
            <div
              key={line}
              className={line.startsWith("+") ? "add" : line.startsWith("-") ? "del" : ""}
            >
              {line}
            </div>
          ))}
        </pre>
        <div className="reviews">
          {change.reviews.map((r) => (
            <ReviewCard key={r.agent} review={r} />
          ))}
        </div>
      </div>
    </div>
  );
}

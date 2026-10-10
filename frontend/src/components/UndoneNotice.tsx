import { Link } from "react-router";
import type { Change } from "../data/mock";
import { type UndoneNotice, undoneNotice } from "../lib/commitState";
import { changePath } from "../lib/projectPath";
import { UndoIcon } from "./icons";

/**
 * The state icon of a discarded or reverted commit: an amber "undo" arrow. The state is also said
 * in words (its text alternative is the label), so the colour is never the only signal.
 */
export function UndoneStatusIcon({ notice, size = 16 }: { notice: UndoneNotice; size?: number }) {
  return (
    <span className="status-icon" data-tone="warning" role="img" aria-label={notice.label}>
      <UndoIcon size={size} />
    </span>
  );
}

/** The label shown in the middle of a channel row: the headline in capitals and its subtitle. */
export function UndoneLabel({ notice }: { notice: UndoneNotice }) {
  return (
    <p className="undone-label" data-state={notice.state}>
      <strong>{notice.label}</strong>
      <span>{notice.subtitle}</span>
    </p>
  );
}

/** The same notice as a banner at the top of the change detail, linking to the revert if known. */
export function UndoneBanner({ change, slug }: { change: Change; slug: string }) {
  const notice = undoneNotice(change);
  if (!notice) return null;
  return (
    <aside className="undone-banner" data-state={notice.state} aria-label="Estado del commit">
      <UndoIcon size={20} />
      <div>
        <strong>{notice.label}</strong>
        <p>
          {notice.state === "reverted" && change.revertedBy ? (
            <>
              Revertido por{" "}
              <Link className="mono" to={changePath(slug, change.revertedBy.id)}>
                {change.revertedBy.sha.slice(0, 7)}
              </Link>
              .
            </>
          ) : (
            `${notice.subtitle}.`
          )}{" "}
          Sus reviews se conservan.
        </p>
      </div>
    </aside>
  );
}

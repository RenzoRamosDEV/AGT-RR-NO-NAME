import type { ReviewAggregate } from "../data/mock";
import { AGGREGATE_LABEL } from "../lib/reviewStatus";
import { AlertIcon, CheckCircleIcon, ClockIcon, DotCircleIcon, XCircleIcon } from "./icons";

const ICON = {
  pending: ClockIcon,
  running: DotCircleIcon,
  partial_failed: AlertIcon,
  failed: XCircleIcon,
  completed: CheckCircleIcon,
} as const;

const TONE: Record<ReviewAggregate, string> = {
  pending: "warning",
  running: "warning",
  partial_failed: "warning",
  failed: "danger",
  completed: "success",
};

/** GitHub-like state icon of a change; its text alternative is the state label. */
export function StatusIcon({
  status,
  size = 16,
}: {
  status: ReviewAggregate | undefined;
  size?: number;
}) {
  if (!status) return <span className="status-icon" data-tone="neutral" aria-hidden="true" />;
  const Icon = ICON[status];
  return (
    <span
      className="status-icon"
      data-tone={TONE[status]}
      role="img"
      aria-label={AGGREGATE_LABEL[status]}
    >
      <Icon size={size} />
    </span>
  );
}

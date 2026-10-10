import { Busy } from "../../components/Busy";
import { agentLabel } from "../../components/ui/AgentAvatar";
import type { Change } from "../../data/mock";
import { pendingAgents } from "../../lib/pending";

/**
 * One orb per configured agent that has not delivered its review of the current run. It goes away
 * on its own when the review arrives (the page keeps refreshing while the change is in progress).
 */
export function PendingAgents({
  change,
  agentNames,
}: {
  change: Pick<Change, "reviewStatus" | "reviews" | "run">;
  agentNames: readonly string[] | null;
}) {
  const waiting = pendingAgents(change, agentNames);
  if (waiting !== null && waiting.length === 0) return null;
  return (
    <ul className="pending-agents" aria-label="Agentes pendientes">
      {waiting === null ? (
        <li>
          <Busy activity="agent" label="Esperando a los agentes…" inline />
        </li>
      ) : (
        waiting.map((agent) => (
          <li key={agent}>
            <Busy activity="agent" label={`${agentLabel(agent)} está revisando…`} inline />
          </li>
        ))
      )}
    </ul>
  );
}

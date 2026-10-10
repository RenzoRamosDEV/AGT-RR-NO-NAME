import { Busy } from "./Busy";

/** "Agent is thinking" indicator: an orb next to the label, or a static "…" under reduced motion. */
export function AgentThinking({ label }: { label: string }) {
  return <Busy activity="agent" label={label} className="thinking" />;
}

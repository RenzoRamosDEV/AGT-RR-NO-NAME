import { ThinkingOrb } from "thinking-orbs";
import { useReducedMotion } from "../lib/useReducedMotion";

/** "Agent is thinking" indicator: animated orb, or static text under reduced motion. */
export function AgentThinking({ label }: { label: string }) {
  const reduced = useReducedMotion();
  return (
    <output className="thinking">
      {reduced ? (
        <span aria-hidden="true">…</span>
      ) : (
        <ThinkingOrb state="working" size={20} theme="dark" aria-label={label} />
      )}
      <span>{label}</span>
    </output>
  );
}

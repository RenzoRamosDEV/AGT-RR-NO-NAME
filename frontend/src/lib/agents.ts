import { agentLabel } from "../components/ui/AgentAvatar";

/** Shown while the configured agents are unknown (loading or a server that does not report them). */
const UNKNOWN_AGENTS = "los agentes configurados";

/** `Claude`, `Claude y Codex`, `A, B y C`: the configured agents as a Spanish enumeration. */
export function agentList(names: readonly string[] | null | undefined): string {
  if (!names || names.length === 0) return UNKNOWN_AGENTS;
  const labels = names.map(agentLabel);
  if (labels.length === 1) return labels[0] as string;
  return `${labels.slice(0, -1).join(", ")} y ${labels[labels.length - 1]}`;
}

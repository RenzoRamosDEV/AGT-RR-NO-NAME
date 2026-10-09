import type { AgentName } from "../../data/mock";

const LABEL: Record<AgentName, string> = { claude: "Claude", codex: "Codex" };

export function agentLabel(agent: AgentName): string {
  return LABEL[agent];
}

export function AgentAvatar({ agent }: { agent: AgentName }) {
  return (
    <span className="avatar" aria-hidden="true">
      {LABEL[agent][0]}
    </span>
  );
}

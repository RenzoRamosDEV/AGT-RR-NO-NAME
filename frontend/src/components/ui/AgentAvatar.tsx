const LABEL: Record<string, string> = { claude: "Claude", codex: "Codex" };

/** Display name of an agent; unknown agents (the API sends a free string) are capitalized. */
export function agentLabel(agent: string): string {
  return LABEL[agent.toLowerCase()] ?? (agent.charAt(0).toUpperCase() + agent.slice(1) || "?");
}

export function AgentAvatar({ agent }: { agent: string }) {
  return (
    <span className="avatar" aria-hidden="true">
      {agentLabel(agent)[0]}
    </span>
  );
}

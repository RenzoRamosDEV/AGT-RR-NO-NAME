const LABEL: Record<string, string> = { claude: "Claude", codex: "Codex" };

/** Display name of an agent; unknown agents (the API sends a free string) are capitalized. */
export function agentLabel(agent: string): string {
  return LABEL[agent.toLowerCase()] ?? (agent.charAt(0).toUpperCase() + agent.slice(1) || "?");
}

/** One or two letters: the first of each of the first two words (`agent_1` -> `A1`). */
export function agentInitials(agent: string): string {
  const words = agentLabel(agent)
    .split(/[^A-Za-z0-9]+/)
    .filter(Boolean);
  if (words.length === 0) return "?";
  return words
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
}

export function AgentAvatar({ agent }: { agent: string }) {
  return (
    <span className="avatar" aria-hidden="true">
      {agentInitials(agent)}
    </span>
  );
}

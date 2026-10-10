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

/** Stable hue (0-359) per agent name, so each agent keeps its color on every page. */
export function agentHue(agent: string): number {
  let hash = 0;
  for (const char of agent.toLowerCase()) hash = (Math.imul(hash, 31) + char.charCodeAt(0)) >>> 0;
  // Final mix: names that differ in one character (`agent_1`, `agent_2`) must not get the same hue.
  hash = Math.imul(hash ^ (hash >>> 16), 2246822507) >>> 0;
  hash = Math.imul(hash ^ (hash >>> 13), 3266489909) >>> 0;
  return ((hash ^ (hash >>> 16)) >>> 0) % 360;
}

export function AgentAvatar({ agent, size = "md" }: { agent: string; size?: "sm" | "md" }) {
  return (
    <span
      className="avatar"
      data-size={size}
      style={{ "--avatar-hue": agentHue(agent) } as React.CSSProperties}
      aria-hidden="true"
    >
      {agentInitials(agent)}
    </span>
  );
}

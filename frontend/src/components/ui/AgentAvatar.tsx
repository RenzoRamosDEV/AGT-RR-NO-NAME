import { useState } from "react";
import claudeLogo from "../../assets/agents/claude.jpg";
import codexLogo from "../../assets/agents/codex.jpg";

const LABEL: Record<string, string> = { claude: "Claude", codex: "Codex" };

/** Agents that have a logo; every other agent gets its initials on a stable color. */
const LOGO: Record<string, string> = { claude: claudeLogo, codex: codexLogo };

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

/** The logo of an agent, or `undefined` when it has none (any agent but Claude and Codex). */
export function agentLogo(agent: string): string | undefined {
  return LOGO[agent.toLowerCase()];
}

export type AvatarSize = 16 | 20 | 28 | 36;

/**
 * An agent's avatar: its logo (Claude, Codex) or its initials on a stable color, as a rounded
 * square like a Slack app. The image is decorative by default because the name is almost always
 * next to it; pass `decorative={false}` where it stands alone and it gets the agent's name as
 * `alt`. A logo that fails to load falls back to the initials.
 */
export function AgentAvatar({
  agent,
  size = 28,
  decorative = true,
}: {
  agent: string;
  size?: AvatarSize;
  decorative?: boolean;
}) {
  const logo = agentLogo(agent);
  // The failed state belongs to the logo's URL, so a different agent starts clean.
  const [failed, setFailed] = useState<string | null>(null);
  const showLogo = logo !== undefined && failed !== logo;
  const name = agentLabel(agent);
  return (
    <span
      className="avatar"
      data-size={size}
      data-kind={showLogo ? "logo" : "initials"}
      style={
        {
          width: size,
          height: size,
          fontSize: Math.round(size * 0.38),
          "--avatar-hue": agentHue(agent),
        } as React.CSSProperties
      }
      aria-hidden={decorative ? true : undefined}
      role={!decorative && !showLogo ? "img" : undefined}
      aria-label={!decorative && !showLogo ? name : undefined}
    >
      {showLogo ? (
        <img
          src={logo}
          alt={decorative ? "" : name}
          width={size}
          height={size}
          loading="lazy"
          decoding="async"
          draggable={false}
          onError={() => setFailed(logo)}
        />
      ) : (
        agentInitials(agent)
      )}
    </span>
  );
}

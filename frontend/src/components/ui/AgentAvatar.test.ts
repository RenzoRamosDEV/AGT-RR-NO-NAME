import { describe, expect, it } from "vitest";
import { agentInitials, agentLabel } from "./AgentAvatar";

describe("agentLabel / agentInitials", () => {
  it("gives a proper name only to Claude and Codex", () => {
    expect(agentLabel("claude")).toBe("Claude");
    expect(agentLabel("CODEX")).toBe("Codex");
    expect(agentLabel("agent_1")).toBe("Agent_1");
  });

  it("uses the initials of the first two words", () => {
    expect(agentInitials("agent_1")).toBe("A1");
    expect(agentInitials("my-fancy-bot")).toBe("MF");
    expect(agentInitials("claude")).toBe("C");
    expect(agentInitials("")).toBe("?");
    expect(agentInitials("__")).toBe("?");
  });
});

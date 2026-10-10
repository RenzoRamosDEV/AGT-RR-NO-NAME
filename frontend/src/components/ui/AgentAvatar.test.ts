import { describe, expect, it } from "vitest";
import { agentHue, agentInitials, agentLabel } from "./AgentAvatar";

describe("agentHue", () => {
  it("is stable for the same name, whatever its case", () => {
    expect(agentHue("agent_1")).toBe(agentHue("agent_1"));
    expect(agentHue("Claude")).toBe(agentHue("claude"));
  });

  it("stays inside the color wheel", () => {
    for (const name of ["a", "agent_1", "claude", "codex", "x".repeat(200), "ñandú"]) {
      const hue = agentHue(name);
      expect(hue).toBeGreaterThanOrEqual(0);
      expect(hue).toBeLessThan(360);
    }
  });

  it("gives names that differ in one character clearly different colors", () => {
    // Regression: a plain `hash % 360` gave `agent_1` and `agent_2` hues one degree apart, so both
    // looked the same in the channel.
    const gaps = [1, 2, 3, 4, 5].map((n) => {
      const d = Math.abs(agentHue(`agent_${n}`) - agentHue(`agent_${n + 1}`));
      return Math.min(d, 360 - d);
    });
    expect(Math.min(...gaps)).toBeGreaterThan(15);
  });
});

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

import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import App from "../App";
import { agentLogo } from "../components/ui/AgentAvatar";
import type { AgentStat } from "../data/mock";
import { DataSourceProvider } from "../data/source";
import type { DataSource } from "../lib/api";
import { makeChange, makeFinding, makeReview, makeSource } from "../test/fixtures";

function renderWith(source: Partial<DataSource>, path: string) {
  return render(
    <DataSourceProvider source={makeSource(source)}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </DataSourceProvider>,
  );
}

const srcOf = (element: Element | null) => element?.querySelector("img")?.getAttribute("src");

describe("agent logos across the app", () => {
  it("shows the logo of Claude and Codex as the checks of a channel row, and initials for others", async () => {
    const change = makeChange({
      id: "c1",
      title: "con checks",
      reviewStatus: "completed",
      reviews: [
        makeReview({ agent: "claude", partial: true }),
        makeReview({ agent: "codex", partial: true }),
        makeReview({ agent: "agent_9", partial: true }),
      ],
    });
    renderWith({ changes: async () => ({ items: [change], nextCursor: null }) }, "/p/demo");
    const checks = await screen.findByRole("list", { name: "Checks de los agentes" });
    const [claude, codex, other] = within(checks).getAllByRole("img");
    expect(srcOf(claude as Element)).toBe(agentLogo("claude"));
    expect(srcOf(codex as Element)).toBe(agentLogo("codex"));
    expect(srcOf(other as Element)).toBeUndefined();
    expect(other).toHaveTextContent("A9");
  });

  it("shows the logo of the agent a change is still waiting for", async () => {
    const change = makeChange({
      id: "c2",
      title: "en curso",
      reviewStatus: "pending",
      reviews: [],
    });
    renderWith(
      {
        changes: async () => ({ items: [change], nextCursor: null }),
        health: async () => ({ status: "ok", dependencies: [], agentNames: ["claude", "codex"] }),
      },
      "/p/demo",
    );
    const waiting = await screen.findByRole("list", { name: "Agentes pendientes" });
    const items = within(waiting).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(srcOf(items[0] as Element)).toBe(agentLogo("claude"));
    expect(srcOf(items[1] as Element)).toBe(agentLogo("codex"));
    expect(items[0]).toHaveTextContent("Claude está revisando…");
  });

  it("shows the agents' logos in the thread of a change", async () => {
    const change = makeChange({
      id: "d1",
      reviewStatus: "completed",
      run: 1,
      reviews: [
        makeReview({ agent: "claude", run: 1, summary: "bien", findings: [makeFinding()] }),
        makeReview({ agent: "codex", run: 1, summary: "mal", findings: [] }),
      ],
    });
    renderWith({ change: async () => change }, "/p/demo/changes/d1");
    const thread = await screen.findByRole("region", { name: "Revisión de los agentes" });
    const avatars = [...thread.querySelectorAll(".message > .avatar")];
    expect(avatars.map((a) => srcOf(a))).toEqual([agentLogo("claude"), agentLogo("codex")]);
  });

  it("shows the logo next to each agent in the statistics table", async () => {
    const stat = (agent: string): AgentStat => ({
      agent,
      total: 3,
      completed: 3,
      failed: 0,
      avgDurationMs: 1000,
      avgScore: 8,
    });
    renderWith({ agentStats: async () => [stat("claude"), stat("agent_1")] }, "/stats");
    const claude = (await screen.findByRole("rowheader", { name: "Claude" })) as HTMLElement;
    expect(srcOf(claude)).toBe(agentLogo("claude"));
    const other = screen.getByRole("rowheader", { name: "Agent_1" });
    expect(srcOf(other)).toBeUndefined();
  });

  it("lists the configured agents in Settings with their logos", async () => {
    renderWith(
      { health: async () => ({ status: "ok", dependencies: [], agentNames: ["codex", "claude"] }) },
      "/settings",
    );
    const list = await screen.findByRole("list", { name: "Agentes activos" });
    const items = within(list).getAllByRole("listitem");
    expect(items.map((i) => srcOf(i))).toEqual([agentLogo("codex"), agentLogo("claude")]);
  });
});

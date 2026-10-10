import { act, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import type { Change, Health } from "../data/mock";
import { DataSourceProvider } from "../data/source";
import type { DataSource } from "../lib/api";
import { PollingProvider } from "../lib/polling";
import { makeChange, makeReview, makeSource } from "../test/fixtures";

vi.mock("thinking-orbs", () => ({
  ThinkingOrb: (props: { state: string }) => <canvas data-orb data-state={props.state} />,
}));

const POLL_MS = 1000;
const AGENTS = ["agent_1", "agent_2"];

function renderApp(source: DataSource) {
  return render(
    <DataSourceProvider source={source}>
      <PollingProvider intervalMs={POLL_MS}>
        <MemoryRouter initialEntries={["/p/demo/changes/p1"]}>
          <App />
        </MemoryRouter>
      </PollingProvider>
    </DataSourceProvider>,
  );
}

const tick = (ms: number) =>
  act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });

const orbs = () => document.querySelectorAll("canvas[data-orb]");

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("pending agents follow the live refresh", () => {
  it("each orb goes away when its review arrives, and nothing flickers in between", async () => {
    let current: Change = makeChange({
      id: "p1",
      title: "en curso",
      run: 1,
      reviewStatus: "pending",
      reviews: [],
    });
    renderApp(
      makeSource({
        health: async (): Promise<Health> => ({
          status: "ok",
          dependencies: [],
          agentNames: AGENTS,
        }),
        change: async () => current,
      }),
    );
    await tick(0);
    expect(screen.getByText("Agent_1 está revisando…")).toBeInTheDocument();
    expect(screen.getByText("Agent_2 está revisando…")).toBeInTheDocument();
    expect(orbs()).toHaveLength(2);

    // A silent refresh with nothing new keeps the same two orbs and shows no loading orb.
    await tick(POLL_MS);
    expect(orbs()).toHaveLength(2);
    expect(screen.queryByText("Cargando change…")).toBeNull();

    current = {
      ...current,
      reviewStatus: "running",
      reviews: [makeReview({ agent: "agent_1", run: 1, summary: "ok" })],
    };
    await tick(POLL_MS);
    expect(screen.queryByText("Agent_1 está revisando…")).toBeNull();
    expect(screen.getByText("Agent_2 está revisando…")).toBeInTheDocument();

    current = {
      ...current,
      reviewStatus: "completed",
      reviews: AGENTS.map((agent) => makeReview({ agent, run: 1, summary: "ok" })),
    };
    await tick(POLL_MS);
    expect(screen.queryByRole("list", { name: "Agentes pendientes" })).toBeNull();
    expect(orbs()).toHaveLength(0);
  });
});

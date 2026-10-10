import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import type { Change, Health } from "../data/mock";
import { DataSourceProvider } from "../data/source";
import type { DataSource, ProjectRef } from "../lib/api";
import { clearIngestToken, setIngestToken } from "../lib/ingestToken";
import { makeChange, makeReview, makeSource } from "../test/fixtures";

// The real orb paints on a canvas, which jsdom lacks: this stand-in records the state it was given.
vi.mock("thinking-orbs", () => ({
  ThinkingOrb: (props: { state: string; size: number; theme: string }) => (
    <canvas data-orb data-state={props.state} data-size={props.size} data-theme={props.theme} />
  ),
}));

const never = <T,>() => new Promise<T>(() => {});

function renderApp(overrides: Partial<DataSource>, path: string) {
  return render(
    <DataSourceProvider source={makeSource(overrides)}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </DataSourceProvider>,
  );
}

/** The orb drawn next to a label: its state, and that it is the 20 px dark one. */
function orbNear(label: string | RegExp) {
  const busy = screen.getByText(label).closest(".busy");
  const orb = busy?.querySelector("canvas[data-orb]") ?? null;
  expect(orb, `no orb next to ${label}`).not.toBeNull();
  expect(orb).toHaveAttribute("data-size", "20");
  expect(orb).toHaveAttribute("data-theme", "dark");
  return orb?.getAttribute("data-state");
}

const allOrbs = () => [...document.querySelectorAll("canvas[data-orb]")];

const GITHUB: ProjectRef = {
  slug: "acme/widgets",
  name: "acme/widgets",
  path: "/home/me/acme/widgets",
  hooksInstalled: true,
  github: true,
};

beforeEach(clearIngestToken);
afterEach(() => vi.restoreAllMocks());

describe("loads show an orb of their own state", () => {
  it("channel, detail and statistics are searching", async () => {
    const { unmount } = renderApp({ changes: never }, "/p/demo");
    expect(orbNear("Cargando cambios…")).toBe("searching");
    unmount();

    const detail = renderApp({ change: never }, "/p/demo/changes/c1");
    expect(orbNear("Cargando change…")).toBe("searching");
    detail.unmount();

    renderApp({ agentStats: never }, "/stats");
    expect(orbNear("Cargando estadísticas…")).toBe("searching");
  });

  it("the sidebar and the first-project redirect are searching", async () => {
    renderApp({ projects: never }, "/");
    expect(orbNear("Cargando…")).toBe("searching");
    expect(orbNear("Cargando proyectos…")).toBe("searching");
  });

  it("the diagnostics and the project list in Settings use their own states", async () => {
    renderApp({ health: never, projects: never }, "/settings");
    expect(orbNear("Comprobando dependencias…")).toBe("connecting");
    expect(orbNear("Cargando proyectos…")).toBe("searching");
  });

  it("refreshing the diagnostics brings the connecting orb back", async () => {
    let hang = false;
    const ok: Health = { status: "ok", dependencies: [], agentNames: ["claude"] };
    renderApp({ health: async () => (hang ? never() : ok) }, "/settings");
    await screen.findByRole("heading", { name: "Diagnóstico" });
    expect(screen.queryByText("Comprobando dependencias…")).toBeNull();
    hang = true;
    await userEvent.click(screen.getByRole("button", { name: "Actualizar" }));
    expect(orbNear("Comprobando dependencias…")).toBe("connecting");
  });

  it("opening a thread whose full reviews are loading is searching", async () => {
    const light = makeChange({
      id: "c1",
      title: "ligero",
      reviewStatus: "completed",
      run: 1,
      reviews: [makeReview({ agent: "claude", partial: true, run: 1 })],
    });
    renderApp(
      {
        changes: async () => ({ items: [light], nextCursor: null }),
        change: never,
      },
      "/p/demo",
    );
    await userEvent.click(await screen.findByRole("button", { name: "Ver respuestas" }));
    expect(orbNear("Cargando respuestas…")).toBe("searching");
  });
});

describe("actions in progress show an orb inside their disabled button", () => {
  it("«Cargar más» is working", async () => {
    const changes = vi.fn<DataSource["changes"]>(async (_slug, query) =>
      query?.cursor
        ? never()
        : { items: [makeChange({ id: "a", title: "cambio a" })], nextCursor: "cur" },
    );
    renderApp({ changes }, "/p/demo");
    await userEvent.click(await screen.findByRole("button", { name: "Cargar más" }));
    const button = screen.getByRole("button", { name: "Cargando…" });
    expect(button).toBeDisabled();
    expect(within(button).getByText("Cargando…").closest(".busy")).not.toBeNull();
    expect(orbNear("Cargando…")).toBe("working");
  });

  it("«Reintentar review» is solving", async () => {
    setIngestToken("tok");
    const failed = makeChange({
      id: "d1",
      title: "detalle",
      reviewStatus: "failed",
      run: 1,
      reviews: [makeReview({ status: "failed", run: 1 })],
    });
    renderApp({ change: async () => failed, retry: never }, "/p/demo/changes/d1");
    await userEvent.click(await screen.findByRole("button", { name: "Reintentar review" }));
    expect(screen.getByRole("button", { name: "Reintentando…" })).toBeDisabled();
    expect(orbNear("Reintentando…")).toBe("solving");
  });

  it("adding a project is connecting", async () => {
    setIngestToken("tok");
    renderApp({ projects: async () => [], addProject: never }, "/");
    const nav = within(await screen.findByRole("navigation", { name: "Principal" }));
    await userEvent.click(await nav.findByRole("button", { name: "Añadir proyecto" }));
    const dialog = await screen.findByRole("dialog", { name: "Añadir proyecto" });
    await userEvent.type(within(dialog).getByLabelText("Ruta del repositorio"), "/home/me/repo");
    await userEvent.click(within(dialog).getByRole("button", { name: "Añadir" }));
    expect(within(dialog).getByRole("button", { name: "Añadiendo…" })).toBeDisabled();
    expect(orbNear("Añadiendo…")).toBe("connecting");
  });

  it("syncing PRs and removing a project are connecting", async () => {
    setIngestToken("tok");
    renderApp(
      { projects: async () => [GITHUB], syncPrs: never, removeProject: never },
      "/settings",
    );
    await userEvent.click(await screen.findByRole("button", { name: /Sincronizar PRs/ }));
    expect(screen.getByRole("button", { name: "Sincronizando…" })).toBeDisabled();
    expect(orbNear("Sincronizando…")).toBe("connecting");

    await userEvent.click(screen.getByRole("button", { name: "Quitar proyecto acme/widgets" }));
    const dialog = await screen.findByRole("dialog", { name: "Quitar acme/widgets" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Quitar proyecto" }));
    expect(within(dialog).getByRole("button", { name: "Quitando…" })).toBeDisabled();
    expect(orbNear("Quitando…")).toBe("connecting");
  });
});

describe("agents the change is still waiting for", () => {
  const AGENTS = ["agent_1", "agent_2"];
  const health = async (): Promise<Health> => ({
    status: "ok",
    dependencies: [],
    agentNames: AGENTS,
  });
  const detail = (over: Partial<Change>) =>
    makeChange({ id: "p1", title: "pendiente", run: 1, ...over });

  it("the detail shows one working orb per agent while nothing has arrived", async () => {
    renderApp(
      { health, change: async () => detail({ reviewStatus: "pending", reviews: [] }) },
      "/p/demo/changes/p1",
    );
    expect(await screen.findByText("Agent_1 está revisando…")).toBeInTheDocument();
    expect(orbNear("Agent_1 está revisando…")).toBe("working");
    expect(orbNear("Agent_2 está revisando…")).toBe("working");
    expect(screen.getByRole("list", { name: "Agentes pendientes" })).toBeInTheDocument();
  });

  it("with a partial review only the agent that has not answered is left", async () => {
    renderApp(
      {
        health,
        change: async () =>
          detail({
            reviewStatus: "running",
            reviews: [makeReview({ agent: "agent_1", run: 1, summary: "ok" })],
          }),
      },
      "/p/demo/changes/p1",
    );
    expect(await screen.findByText("Agent_2 está revisando…")).toBeInTheDocument();
    expect(screen.queryByText("Agent_1 está revisando…")).toBeNull();
  });

  it("after a retry both agents are pending again for the new run", async () => {
    renderApp(
      {
        health,
        change: async () =>
          detail({
            run: 2,
            reviewStatus: "pending",
            reviews: AGENTS.map((agent) => makeReview({ agent, status: "failed", run: 1 })),
          }),
      },
      "/p/demo/changes/p1",
    );
    expect(await screen.findByText("Agent_1 está revisando…")).toBeInTheDocument();
    expect(screen.getByText("Agent_2 está revisando…")).toBeInTheDocument();
  });

  it.each(["completed", "failed", "partial_failed"] as const)(
    "a %s change shows no pending agents",
    async (reviewStatus) => {
      renderApp(
        {
          health,
          change: async () =>
            detail({ reviewStatus, reviews: [makeReview({ agent: "agent_1", run: 1 })] }),
        },
        "/p/demo/changes/p1",
      );
      await screen.findByRole("heading", { name: "pendiente" });
      expect(screen.queryByRole("list", { name: "Agentes pendientes" })).toBeNull();
      expect(allOrbs()).toHaveLength(0);
    },
  );

  it("shows a single generic orb, not invented names, while the agents are unknown", async () => {
    renderApp(
      { health: never, change: async () => detail({ reviewStatus: "pending", reviews: [] }) },
      "/p/demo/changes/p1",
    );
    expect(await screen.findByText("Esperando a los agentes…")).toBeInTheDocument();
    expect(orbNear("Esperando a los agentes…")).toBe("working");
    expect(screen.queryByText(/está revisando/)).toBeNull();
  });

  it("the channel card of a pending change lists the agents it waits for", async () => {
    const waiting = makeChange({
      id: "w1",
      title: "esperando",
      reviewStatus: "running",
      run: 1,
      reviews: [makeReview({ agent: "agent_2", run: 1, partial: true })],
    });
    const done = makeChange({
      id: "d1",
      title: "terminado",
      reviewStatus: "completed",
      run: 1,
      reviews: AGENTS.map((agent) => makeReview({ agent, run: 1, partial: true })),
    });
    renderApp(
      { health, changes: async () => ({ items: [waiting, done], nextCursor: null }) },
      "/p/demo",
    );
    expect(await screen.findByText("Agent_1 está revisando…")).toBeInTheDocument();
    expect(screen.queryByText("Agent_2 está revisando…")).toBeNull();
    // Only the waiting card has orbs: the finished one does not.
    expect(allOrbs()).toHaveLength(1);
  });
});

describe("reduced motion", () => {
  it("draws no canvas anywhere but keeps every label", async () => {
    vi.spyOn(window, "matchMedia").mockImplementation(
      (query: string) =>
        ({
          matches: query.includes("reduce"),
          media: query,
          addEventListener: () => {},
          removeEventListener: () => {},
        }) as unknown as MediaQueryList,
    );
    renderApp({ changes: never, health: never }, "/p/demo");
    expect(screen.getByText("Cargando cambios…")).toBeInTheDocument();
    expect(allOrbs()).toHaveLength(0);
  });
});

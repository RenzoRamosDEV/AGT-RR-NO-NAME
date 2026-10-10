import { render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import type { Change } from "../data/mock";
import { DataSourceProvider } from "../data/source";
import type { DataSource } from "../lib/api";
import { makeChange, makeReview, makeSource } from "../test/fixtures";

// Canvas-based effects cannot paint in jsdom: the orbs are stood in for, as in the orb tests.
vi.mock("thinking-orbs", () => ({
  ThinkingOrb: (props: { state: string }) => <canvas data-orb data-state={props.state} />,
}));

function renderApp(overrides: Partial<DataSource>, path: string) {
  return render(
    <DataSourceProvider source={makeSource(overrides)}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </DataSourceProvider>,
  );
}

const channelOf = (items: Change[]): Partial<DataSource> => ({
  changes: async () => ({ items, nextCursor: null }),
});

afterEach(() => vi.restoreAllMocks());

describe("border-beam marks only what is in progress", () => {
  const items = [
    makeChange({ id: "p", title: "cambio pendiente", reviewStatus: "pending" }),
    makeChange({
      id: "r",
      title: "cambio en curso",
      reviewStatus: "running",
      reviews: [makeReview({ agent: "claude" })],
    }),
    makeChange({
      id: "ok",
      title: "cambio completado",
      reviewStatus: "completed",
      reviews: [makeReview({ agent: "claude" }), makeReview({ agent: "codex" })],
    }),
    makeChange({
      id: "ko",
      title: "cambio fallido",
      reviewStatus: "failed",
      reviews: [makeReview({ agent: "claude", status: "failed" })],
    }),
  ];

  it("the channel puts a beam on pending and running rows, and on nothing else", async () => {
    renderApp(channelOf(items), "/p/demo");
    await screen.findByText("cambio pendiente");
    await waitFor(() => expect(document.querySelectorAll(".beam")).toHaveLength(2));

    const rowOf = (title: string) => screen.getByText(title).closest("li.change") as HTMLElement;
    expect(rowOf("cambio pendiente").querySelector(".beam")).not.toBeNull();
    expect(rowOf("cambio en curso").querySelector(".beam")).not.toBeNull();
    expect(rowOf("cambio completado").querySelector(".beam")).toBeNull();
    expect(rowOf("cambio fallido").querySelector(".beam")).toBeNull();
  });

  it("a row that finishes loses its beam on the next refresh, and keeps its content", async () => {
    // The same change, first pending and then completed (what the 5 s polling brings).
    const pending = makeChange({ id: "x", title: "se termina", reviewStatus: "pending" });
    const done = makeChange({
      id: "x",
      title: "se termina",
      reviewStatus: "completed",
      reviews: [makeReview({ agent: "claude" })],
    });
    const { rerender } = render(
      <DataSourceProvider source={makeSource(channelOf([pending]))}>
        <MemoryRouter initialEntries={["/p/demo"]}>
          <App />
        </MemoryRouter>
      </DataSourceProvider>,
    );
    await waitFor(() => expect(document.querySelectorAll(".beam")).toHaveLength(1));
    rerender(
      <DataSourceProvider source={makeSource(channelOf([done]))}>
        <MemoryRouter initialEntries={["/p/demo"]} key="again">
          <App />
        </MemoryRouter>
      </DataSourceProvider>,
    );
    await screen.findByText("se termina");
    await waitFor(() => expect(document.querySelectorAll(".beam")).toHaveLength(0));
  });

  it("the detail puts the beam on the agents' panel while a review is missing", async () => {
    const running = makeChange({
      id: "r",
      title: "cambio en curso",
      reviewStatus: "running",
      run: 1,
      reviews: [makeReview({ agent: "claude" })],
    });
    renderApp({ change: async () => running }, "/p/demo/changes/r");
    const panel = await screen.findByRole("region", { name: "Revisión de los agentes" });
    await waitFor(() => expect(panel.closest(".beam")).not.toBeNull());
  });

  it("the detail leaves the panel alone once the change is completed", async () => {
    const done = makeChange({
      id: "ok",
      title: "cambio completado",
      reviewStatus: "completed",
      run: 1,
      reviews: [makeReview({ agent: "claude" }), makeReview({ agent: "codex" })],
    });
    renderApp({ change: async () => done }, "/p/demo/changes/ok");
    const panel = await screen.findByRole("region", { name: "Revisión de los agentes" });
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(panel.closest(".beam")).toBeNull();
  });
});

describe("the key actions use the metal button, the empty states the hero picture", () => {
  it("the retry button of a failed change is the neutral metal-style button", async () => {
    const failed = makeChange({
      id: "ko",
      title: "cambio fallido",
      reviewStatus: "failed",
      run: 1,
      reviews: [makeReview({ agent: "claude", status: "failed", error: "x" })],
    });
    renderApp({ change: async () => failed }, "/p/demo/changes/ko");
    const button = await screen.findByRole("button", { name: "Reintentar review" });
    expect(button).toHaveClass("btn-metal");
  });

  it("add-project, in Settings and in the empty home, is the metal button", async () => {
    const { unmount } = renderApp({ projects: async () => [] }, "/");
    // The sidebar has its own "add" entry; the one under test is the empty state's call to action.
    const empty = (await screen.findByText("Aún no hay proyectos vigilados.")).closest(
      ".empty-state",
    ) as HTMLElement;
    const inHome = within(empty).getByRole("button", { name: "Añadir proyecto" });
    expect(inHome).toHaveClass("btn-metal");
    expect(inHome).not.toHaveClass("btn-primary");
    unmount();

    renderApp({}, "/settings");
    const box = (await screen.findByRole("heading", { name: "Proyectos vigilados" })).closest(
      "section",
    ) as HTMLElement;
    expect(within(box).getByRole("button", { name: "Añadir proyecto" })).toHaveClass("btn-metal");
  });

  it("the home without projects and a channel without changes show the hero picture", async () => {
    const home = renderApp({ projects: async () => [] }, "/");
    await screen.findByText("Aún no hay proyectos vigilados.");
    expect(home.container.querySelector("img.hero-img")).toBeInTheDocument();
    home.unmount();

    const channel = renderApp(channelOf([]), "/p/demo");
    await screen.findByText("Aún no hay cambios en este canal.");
    expect(channel.container.querySelector("img.hero-img")).toBeInTheDocument();
  });

  it("the not-found page keeps the line illustration: the hero is for the empty states", async () => {
    const { container } = renderApp({}, "/nada/por/aqui");
    await screen.findByRole("heading", { name: "No encontrado" });
    expect(container.querySelector("svg.empty-art")).toBeInTheDocument();
    expect(container.querySelector("img.hero-img")).toBeNull();
  });
});

import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import type { Change, ReviewAggregate } from "../data/mock";
import { DataSourceProvider } from "../data/source";
import type { DataSource } from "../lib/api";
import { PollingProvider } from "../lib/polling";
import { makeChange, makeReview, makeSource } from "../test/fixtures";

const POLL_MS = 1000;

function renderApp(source: DataSource, path: string) {
  return render(
    <DataSourceProvider source={source}>
      <PollingProvider intervalMs={POLL_MS}>
        <MemoryRouter initialEntries={[path]}>
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

function setVisibility(state: "visible" | "hidden") {
  vi.spyOn(document, "visibilityState", "get").mockReturnValue(state);
  document.dispatchEvent(new Event("visibilitychange"));
}

const change = (n: number): Change =>
  makeChange({ id: `c${n}`, title: `cambio-${n}`, reviewStatus: "completed" });

/** Channel source over a mutable list, newest first, with keyset pagination like the API. */
function channelSource(getData: () => Change[], pageSize = 2) {
  return makeSource({
    projects: async () => [{ slug: "demo", name: "demo" }],
    changes: vi.fn(async (_slug: string, query = {}) => {
      const all = getData().filter((c) => !query.q || c.title.includes(query.q));
      const start = query.cursor ? all.findIndex((c) => c.id === query.cursor) + 1 : 0;
      const items = all.slice(start, start + pageSize);
      const more = start + items.length < all.length;
      return { items, nextCursor: more ? items[items.length - 1].id : null };
    }),
  });
}

const titles = () =>
  within(screen.getByRole("main"))
    .getAllByRole("link", { name: /^cambio-/ })
    .map((a) => a.textContent);

beforeEach(() => {
  vi.useFakeTimers();
  // Testing Library only advances fake timers for `jest`; this lets `userEvent` work with vitest's.
  vi.stubGlobal("jest", { advanceTimersByTime: (ms: number) => vi.advanceTimersByTime(ms) });
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("live channel", () => {
  it("shows a new commit on its own, without a loading state, and says when it updated", async () => {
    let data = [change(1)];
    renderApp(
      channelSource(() => data),
      "/p/demo",
    );
    await tick(0);
    expect(titles()).toEqual(["cambio-1"]);

    data = [change(2), ...data];
    await tick(POLL_MS);
    expect(titles()).toEqual(["cambio-2", "cambio-1"]);
    expect(screen.queryByText("Cargando cambios…")).toBeNull();
    expect(screen.getByText("Actualizado ahora")).toBeInTheDocument();
  });

  it("keeps the search text, the filters and every page loaded when a new change arrives", async () => {
    const user = userEvent.setup({ delay: null });
    let data = [change(4), change(3), change(2), change(1)];
    const source = channelSource(() => data);
    renderApp(source, "/p/demo");
    await tick(0);

    await user.type(screen.getByRole("searchbox"), "cambio");
    await tick(400);
    await user.click(screen.getByRole("button", { name: "Commits" }));
    await tick(0);
    expect(titles()).toEqual(["cambio-4", "cambio-3"]);
    await user.click(screen.getByRole("button", { name: "Cargar más" }));
    await tick(0);
    expect(titles()).toEqual(["cambio-4", "cambio-3", "cambio-2", "cambio-1"]);

    // A new change pushes cambio-3 out of the refreshed first page: nothing may be lost or repeated.
    data = [change(5), ...data];
    await tick(POLL_MS);
    expect(titles()).toEqual(["cambio-5", "cambio-4", "cambio-3", "cambio-2", "cambio-1"]);
    expect(screen.getByRole("searchbox")).toHaveValue("cambio");
    expect(screen.getByRole("button", { name: "Commits" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByRole("button", { name: "Cargar más" })).toBeNull();
  });

  it("does not repaint when nothing changed", async () => {
    const source = channelSource(() => [change(1)]);
    renderApp(source, "/p/demo");
    await tick(0);
    const link = screen.getByRole("link", { name: "cambio-1" });
    await tick(3 * POLL_MS);
    expect(source.changes).toHaveBeenCalledTimes(4);
    // Same DOM node: the list was not re-created by the refreshes.
    expect(screen.getByRole("link", { name: "cambio-1" })).toBe(link);
  });

  it("pauses while the tab is hidden and refreshes as soon as it is visible", async () => {
    let data = [change(1)];
    const source = channelSource(() => data);
    renderApp(source, "/p/demo");
    await tick(0);

    setVisibility("hidden");
    data = [change(2), ...data];
    await tick(5 * POLL_MS);
    expect(source.changes).toHaveBeenCalledTimes(1);
    expect(titles()).toEqual(["cambio-1"]);

    setVisibility("visible");
    await tick(0);
    expect(titles()).toEqual(["cambio-2", "cambio-1"]);
  });

  it("keeps showing the list and warns when a refresh fails", async () => {
    const source = channelSource(() => [change(1)]);
    renderApp(source, "/p/demo");
    await tick(0);
    vi.mocked(source.changes).mockRejectedValueOnce(new Error("down"));
    await tick(POLL_MS);
    expect(titles()).toEqual(["cambio-1"]);
    expect(screen.getByText(/No se pudo actualizar/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();

    await tick(POLL_MS);
    expect(screen.queryByText(/No se pudo actualizar/)).toBeNull();
  });
});

describe("live sidebar", () => {
  it("lists a project added elsewhere without reloading", async () => {
    let projects = [{ slug: "demo", name: "demo" }];
    renderApp(makeSource({ projects: async () => projects }), "/settings");
    await tick(0);
    const nav = within(screen.getByRole("navigation", { name: "Principal" }));
    expect(nav.queryByRole("link", { name: /nuevo/ })).toBeNull();

    projects = [...projects, { slug: "me/nuevo", name: "me/nuevo" }];
    await tick(POLL_MS);
    expect(nav.getByRole("link", { name: /me\/nuevo/ })).toBeInTheDocument();
    expect(screen.queryByText("Cargando proyectos…")).toBeNull();
  });
});

describe("live change detail", () => {
  const reviewing = (status: ReviewAggregate) =>
    makeChange({
      id: "c1",
      title: "detalle",
      reviewStatus: status,
      reviews: status === "completed" ? [makeReview({ id: "r1", summary: "todo bien" })] : [],
    });

  it("follows the review while it runs and stops once it has finished", async () => {
    const states: ReviewAggregate[] = ["pending", "running", "completed"];
    let call = 0;
    const source = makeSource({
      change: vi.fn(async () => reviewing(states[Math.min(call++, states.length - 1)])),
    });
    renderApp(source, "/p/demo/changes/c1");
    await tick(0);
    expect(screen.getByText("Pendiente")).toBeInTheDocument();
    expect(screen.getByText("Actualizado ahora")).toBeInTheDocument();

    await tick(POLL_MS);
    expect(screen.getByText("En curso")).toBeInTheDocument();
    await tick(POLL_MS);
    expect(screen.getByText("todo bien")).toBeInTheDocument();
    expect(screen.queryByText(/^Actualizado/)).toBeNull();

    await tick(10 * POLL_MS);
    expect(source.change).toHaveBeenCalledTimes(3);
  });

  it("does not poll a change that is already finished", async () => {
    const source = makeSource({ change: vi.fn(async () => reviewing("completed")) });
    renderApp(source, "/p/demo/changes/c1");
    await tick(10 * POLL_MS);
    expect(source.change).toHaveBeenCalledTimes(1);
  });
});

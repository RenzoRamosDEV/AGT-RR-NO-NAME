import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { DataSourceProvider } from "../data/source";
import { ApiError, type ChangePage, type DataSource } from "../lib/api";
import { makeChange, makeFinding, makeReview, makeSource } from "../test/fixtures";

function renderWith(source: Partial<DataSource>, path: string) {
  const full = makeSource(source);
  return render(
    <DataSourceProvider source={full}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </DataSourceProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("load states", () => {
  it("shows a recoverable error and then the channel after retrying", async () => {
    const changes = vi
      .fn<DataSource["changes"]>()
      .mockRejectedValueOnce(new ApiError("El servidor respondió 503.", 503))
      .mockResolvedValue({ items: [makeChange({ title: "hola" })], nextCursor: null });
    renderWith({ changes }, "/p/demo");
    expect(await screen.findByRole("alert")).toHaveTextContent("503");
    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("hola")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows 'not found' instead of a generic error on 404", async () => {
    renderWith(
      {
        changes: async () => {
          throw new ApiError("x", 404);
        },
      },
      "/p/nope",
    );
    expect(await screen.findByRole("heading", { name: "Proyecto no encontrado" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Reintentar" })).toBeNull();
  });

  it("shows the empty state when the API has no projects", async () => {
    renderWith({ projects: async () => [] }, "/");
    expect(await screen.findByText("Aún no hay proyectos vigilados.")).toBeInTheDocument();
  });
});

describe("load more", () => {
  const page = (ids: string[], nextCursor: string | null): ChangePage => ({
    items: ids.map((id) => makeChange({ id, title: `change ${id}`, sha: `sha${id}` })),
    nextCursor,
  });

  it("appends the next page without duplicates and hides the button at the end", async () => {
    const changes = vi.fn<DataSource["changes"]>(async (_slug, q) =>
      q?.cursor ? page(["b", "c"], null) : page(["a", "b"], "cur1"),
    );
    renderWith({ changes }, "/p/demo");
    await screen.findByText("change a");
    await userEvent.click(screen.getByRole("button", { name: "Cargar más" }));
    await screen.findByText("change c");
    expect(screen.getAllByText("change b")).toHaveLength(1);
    expect(changes).toHaveBeenLastCalledWith("demo", { cursor: "cur1" });
    expect(screen.queryByRole("button", { name: "Cargar más" })).toBeNull();
  });

  it("sends the search and the filters again when loading more", async () => {
    const changes = vi.fn<DataSource["changes"]>(async (_s, q) =>
      q?.cursor ? page(["c"], null) : page(["a", "b"], "cur1"),
    );
    renderWith({ changes }, "/p/demo");
    await screen.findByText("change a");
    await userEvent.click(screen.getByRole("button", { name: "Con fallos" }));
    await userEvent.type(screen.getByRole("searchbox", { name: "Buscar cambios" }), " sha ");
    await waitFor(() =>
      expect(changes).toHaveBeenLastCalledWith("demo", {
        status: ["failed", "partial_failed"],
        q: "sha",
      }),
    );
    await userEvent.click(await screen.findByRole("button", { name: "Cargar más" }));
    await screen.findByText("change c");
    expect(changes).toHaveBeenLastCalledWith("demo", {
      status: ["failed", "partial_failed"],
      q: "sha",
      cursor: "cur1",
    });
  });

  it("keeps what is shown when loading more fails and allows retrying", async () => {
    const changes = vi
      .fn<DataSource["changes"]>()
      .mockResolvedValueOnce(page(["a"], "cur1"))
      .mockRejectedValueOnce(new ApiError("boom", 500))
      .mockResolvedValueOnce(page(["b"], null));
    renderWith({ changes }, "/p/demo");
    await screen.findByText("change a");
    await userEvent.click(screen.getByRole("button", { name: "Cargar más" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se pudieron cargar más cambios.",
    );
    expect(screen.getByText("change a")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("change b")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("restarts the list and the cursor when the kind filter changes", async () => {
    const changes = vi.fn<DataSource["changes"]>(async (_s, q) =>
      q?.kind === "pr" ? page(["p1"], null) : page(["a"], "cur1"),
    );
    renderWith({ changes }, "/p/demo");
    await screen.findByText("change a");
    await userEvent.click(screen.getByRole("button", { name: "PRs" }));
    await screen.findByText("change p1");
    expect(screen.queryByText("change a")).toBeNull();
    expect(screen.queryByRole("button", { name: "Cargar más" })).toBeNull();
    expect(changes).toHaveBeenLastCalledWith("demo", { kind: "pr" });
  });
});

describe("server-side filters", () => {
  const items = (...titles: string[]) =>
    titles.map((title) => makeChange({ id: title, title, reviews: undefined }));

  it("maps each state filter to the server statuses and shows only what the server returns", async () => {
    const changes = vi.fn<DataSource["changes"]>(async (_s, q) => {
      const status = q?.status?.join(",");
      if (status === "pending,running") return { items: items("en curso"), nextCursor: null };
      if (status === "failed,partial_failed")
        return { items: items("con fallo"), nextCursor: null };
      if (status === "completed") return { items: items("completado"), nextCursor: null };
      return { items: items("todos"), nextCursor: null };
    });
    renderWith({ changes }, "/p/demo");
    await screen.findByText("todos");
    for (const [button, title] of [
      ["En curso", "en curso"],
      ["Con fallos", "con fallo"],
      ["Completados", "completado"],
      ["Todos", "todos"],
    ]) {
      await userEvent.click(screen.getByRole("button", { name: button }));
      expect(await screen.findByText(title)).toBeInTheDocument();
    }
    expect(changes.mock.calls.map(([, q]) => q?.status)).toEqual([
      undefined,
      ["pending", "running"],
      ["failed", "partial_failed"],
      ["completed"],
      undefined,
    ]);
  });

  it("sends q, kind and status together and restarts the cursor on every change", async () => {
    const changes = vi.fn<DataSource["changes"]>(async (_s, q) =>
      q?.cursor
        ? { items: items("pagina 2"), nextCursor: null }
        : { items: items("pagina 1"), nextCursor: "cur1" },
    );
    renderWith({ changes }, "/p/demo");
    await userEvent.click(await screen.findByRole("button", { name: "Cargar más" }));
    await screen.findByText("pagina 2");
    await userEvent.click(screen.getByRole("button", { name: "Completados" }));
    await waitFor(() => expect(screen.queryByText("pagina 2")).toBeNull());
    expect(await screen.findByText("pagina 1")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "PRs" }));
    await userEvent.type(screen.getByRole("searchbox", { name: "Buscar cambios" }), "fix");
    await waitFor(() =>
      expect(changes).toHaveBeenLastCalledWith("demo", {
        kind: "pr",
        status: ["completed"],
        q: "fix",
      }),
    );
    expect(changes.mock.calls.at(-1)?.[1]?.cursor).toBeUndefined();
  });

  it("does not send q while the search is blank and debounces typing", async () => {
    const changes = vi.fn<DataSource["changes"]>(async () => ({
      items: items("x"),
      nextCursor: null,
    }));
    renderWith({ changes }, "/p/demo");
    await screen.findByText("x");
    await userEvent.type(screen.getByRole("searchbox", { name: "Buscar cambios" }), "   ");
    await new Promise((resolve) => setTimeout(resolve, 400));
    expect(changes).toHaveBeenCalledTimes(1);
    await userEvent.type(screen.getByRole("searchbox", { name: "Buscar cambios" }), "abc");
    await waitFor(() => expect(changes).toHaveBeenCalledTimes(2));
    expect(changes.mock.calls[1][1]?.q).toBe("abc");
  });

  it("ignores a late response for a filter that is no longer selected", async () => {
    let releaseSlow: (page: ChangePage) => void = () => {};
    const slow = new Promise<ChangePage>((resolve) => {
      releaseSlow = resolve;
    });
    const changes = vi.fn<DataSource["changes"]>(async (_s, q) =>
      q?.kind === "commit" ? slow : { items: items("vigente"), nextCursor: null },
    );
    renderWith({ changes }, "/p/demo");
    await screen.findByText("vigente");
    await userEvent.click(screen.getByRole("button", { name: "Commits" }));
    await userEvent.click(screen.getByRole("button", { name: "PRs" }));
    await screen.findByText("vigente");
    releaseSlow({ items: items("obsoleto"), nextCursor: null });
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(screen.queryByText("obsoleto")).toBeNull();
    expect(screen.getByText("vigente")).toBeInTheDocument();
  });
});

describe("change detail", () => {
  const detail = makeChange({
    id: "d1",
    title: "detalle",
    sha: "0123456789abcdef",
    ref: "feat/x",
    url: "https://github.com/o/r/pull/9",
    diff: "+a",
    reviews: [
      makeReview({
        agent: "claude",
        findings: [makeFinding({ file: "x.py", severity: "low", line: 8, message: "menor" })],
      }),
      makeReview({
        agent: "codex",
        findings: [makeFinding({ file: "x.py", severity: "critical", line: 2, message: "grave" })],
      }),
    ],
  });

  it("groups findings by file, most severe first, with the agent", async () => {
    renderWith({ change: async () => detail }, "/p/demo/changes/d1");
    const panel = await screen.findByRole("region", { name: "Hallazgos" });
    expect(within(panel).getAllByRole("heading", { level: 3 })).toHaveLength(1);
    const items = within(panel).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Crítico");
    expect(items[0]).toHaveTextContent("Codex");
    expect(items[1]).toHaveTextContent("menor");
  });

  // Regresión: con la API real (FakeAgent) salían `N/A` y `L0` y los agentes figuraban como «Claude».
  it("shows unlocated findings under 'Sin archivo' without N/A or L0, and the real agent name", async () => {
    renderWith(
      {
        change: async () => ({
          ...detail,
          reviews: [
            makeReview({
              agent: "agent_1",
              findings: [makeFinding({ file: "N/A", line: 0, severity: "nit", message: "suelto" })],
            }),
            makeReview({
              agent: "agent_2",
              findings: [makeFinding({ file: "x.py", line: 3, message: "localizado" })],
            }),
          ],
        }),
      },
      "/p/demo/changes/d1",
    );
    const panel = await screen.findByRole("region", { name: "Hallazgos" });
    const headings = within(panel).getAllByRole("heading", { level: 3 });
    expect(headings.map((h) => h.textContent)).toEqual(["x.py", "Sin archivo"]);
    expect(panel).not.toHaveTextContent("N/A");
    expect(panel).not.toHaveTextContent("L0");
    expect(panel).toHaveTextContent("L3");
    expect(panel).toHaveTextContent("Agent_1");
    expect(panel).not.toHaveTextContent("Claude");
    const cards = screen.getAllByRole("article");
    expect(cards[0]).toHaveTextContent("Agent_1");
    expect(cards[1]).toHaveTextContent("Agent_2");
    for (const card of cards) expect(card).not.toHaveTextContent("Claude");
    expect(cards[0]).not.toHaveTextContent("N/A");
  });

  it("omits the findings panel when there are none", async () => {
    renderWith(
      { change: async () => ({ ...detail, reviews: [makeReview()] }) },
      "/p/demo/changes/d1",
    );
    await screen.findByLabelText("Diff");
    expect(screen.queryByRole("region", { name: "Hallazgos" })).toBeNull();
  });

  it("opens the change in a new tab only for http(s) URLs", async () => {
    const { unmount } = renderWith({ change: async () => detail }, "/p/demo/changes/d1");
    const link = await screen.findByRole("link", { name: "Abrir en GitHub" });
    expect(link).toHaveAttribute("href", "https://github.com/o/r/pull/9");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
    unmount();
    renderWith(
      { change: async () => ({ ...detail, url: "javascript:alert(1)" }) },
      "/p/demo/changes/d1",
    );
    await screen.findByLabelText("Diff");
    expect(screen.queryByRole("link", { name: "Abrir en GitHub" })).toBeNull();
  });

  it("copies the full SHA and announces it as text", async () => {
    const writeText = vi.fn(async () => {});
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    renderWith({ change: async () => detail }, "/p/demo/changes/d1");
    await userEvent.click(await screen.findByRole("button", { name: "Copiar SHA" }));
    expect(writeText).toHaveBeenCalledWith("0123456789abcdef");
    await waitFor(() => expect(screen.getByText("Copiado")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Copiar rama" }));
    expect(writeText).toHaveBeenLastCalledWith("feat/x");
    Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
  });

  it("announces a failed copy", async () => {
    Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
    document.execCommand = vi.fn(() => false);
    renderWith({ change: async () => detail }, "/p/demo/changes/d1");
    await userEvent.click(await screen.findByRole("button", { name: "Copiar SHA" }));
    expect(await screen.findByText("No se pudo copiar")).toBeInTheDocument();
  });

  it("shows 'not found' for an unknown change", async () => {
    renderWith({}, "/p/demo/changes/zzz");
    expect(await screen.findByRole("heading", { name: "Change no encontrado" })).toBeVisible();
  });
});

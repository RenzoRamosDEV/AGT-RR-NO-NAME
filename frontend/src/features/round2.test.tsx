import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { DataSourceProvider } from "../data/source";
import { ApiError, type ChangePage, type DataSource } from "../lib/api";
import { makeChange, makeFinding, makeReview } from "../test/fixtures";

function renderWith(source: Partial<DataSource>, path: string) {
  const full: DataSource = {
    projects: async () => [{ slug: "demo", name: "demo" }],
    changes: async () => ({ items: [], nextCursor: null }),
    change: async () => {
      throw new ApiError("no", 404);
    },
    ...source,
  };
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
    expect(changes).toHaveBeenLastCalledWith("demo", { kind: undefined, cursor: "cur1" });
    expect(screen.queryByRole("button", { name: "Cargar más" })).toBeNull();
  });

  it("keeps the search while loading more", async () => {
    const changes = async (_s: string, q?: { cursor?: string | null }) =>
      q?.cursor ? page(["c"], null) : page(["a", "b"], "cur1");
    renderWith({ changes }, "/p/demo");
    await screen.findByText("change a");
    await userEvent.type(screen.getByRole("searchbox", { name: "Buscar cambios" }), "sha");
    await userEvent.click(screen.getByRole("button", { name: "Cargar más" }));
    await screen.findByText("change c");
    await userEvent.type(screen.getByRole("searchbox", { name: "Buscar cambios" }), "c");
    expect(screen.queryByText("change a")).toBeNull();
    expect(screen.getByText("change c")).toBeInTheDocument();
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

describe("state filter", () => {
  it("lists only changes with a failed review and ignores changes without review data", async () => {
    const items = [
      makeChange({ id: "ok", title: "sin fallos", reviews: [makeReview()] }),
      makeChange({ id: "ko", title: "con fallo", reviews: [makeReview({ status: "failed" })] }),
      makeChange({ id: "na", title: "sin datos", reviews: undefined }),
    ];
    renderWith({ changes: async () => ({ items, nextCursor: null }) }, "/p/demo");
    await screen.findByText("con fallo");
    await userEvent.click(screen.getByRole("button", { name: "Con fallos" }));
    expect(screen.getByText("con fallo")).toBeInTheDocument();
    expect(screen.queryByText("sin fallos")).toBeNull();
    expect(screen.queryByText("sin datos")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Todos" }));
    expect(screen.getByText("sin datos")).toBeInTheDocument();
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
    expect(items[0]).toHaveTextContent("critical");
    expect(items[0]).toHaveTextContent("Codex");
    expect(items[1]).toHaveTextContent("menor");
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

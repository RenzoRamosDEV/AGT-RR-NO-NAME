import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

function setReducedMotion(reduced: boolean) {
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query: string) =>
      ({
        matches: reduced && query.includes("reduce"),
        media: query,
        addEventListener: () => {},
        removeEventListener: () => {},
      }) as unknown as MediaQueryList,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("navigation", () => {
  it("redirects / to the first project channel and marks it active", async () => {
    renderAt("/");
    expect(await screen.findByRole("heading", { name: "#duelo" })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Principal" });
    expect(await within(nav).findByRole("link", { name: /duelo/ })).toHaveClass("active");
  });

  it("navigates to stats and settings from the sidebar", async () => {
    renderAt("/");
    const nav = screen.getByRole("navigation", { name: "Principal" });
    await screen.findByRole("heading", { name: "#duelo" });
    await userEvent.click(within(nav).getByRole("link", { name: "Estadísticas" }));
    expect(screen.getByRole("heading", { name: "Estadísticas" })).toBeInTheDocument();
    await userEvent.click(within(nav).getByRole("link", { name: "Ajustes" }));
    expect(screen.getByRole("heading", { name: "Ajustes" })).toBeInTheDocument();
  });

  it("reaches interactive controls in order with Tab", async () => {
    renderAt("/p/duelo");
    await screen.findByRole("link", { name: /acme\/widgets/ });
    // Header first (menu, brand, theme), then the sidebar, then the page.
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "Menú" })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("link", { name: "Duelo" })).toHaveFocus();
    for (const theme of ["Tema sistema", "Tema claro", "Tema oscuro"]) {
      await userEvent.tab();
      expect(screen.getByRole("button", { name: theme })).toHaveFocus();
    }
    await userEvent.tab();
    expect(screen.getByRole("button", { name: /Proyectos/ })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("link", { name: /duelo/ })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("link", { name: /acme\/widgets/ })).toHaveFocus();
  });
});

describe("mobile menu", () => {
  it("toggles with the button and closes with Escape", async () => {
    renderAt("/p/duelo");
    const toggle = screen.getByRole("button", { name: "Menú" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    await userEvent.keyboard("{Escape}");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  it("closes after following a link", async () => {
    renderAt("/p/duelo");
    const toggle = screen.getByRole("button", { name: "Menú" });
    await userEvent.click(toggle);
    const nav = screen.getByRole("navigation", { name: "Principal" });
    await userEvent.click(within(nav).getByRole("link", { name: "Estadísticas" }));
    expect(screen.getByRole("button", { name: "Menú" })).toHaveAttribute("aria-expanded", "false");
  });
});

describe("channel search and summary", () => {
  it("filters by SHA and combines with the kind filter", async () => {
    renderAt("/p/duelo");
    await screen.findAllByRole("button", { name: "Ver respuestas" });
    await userEvent.type(screen.getByRole("searchbox", { name: "Buscar cambios" }), "9BE0");
    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: "Ver respuestas" })).toHaveLength(1),
    );
    expect(screen.getByText("feat: exponer ingesta de commits")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Commits" }));
    expect(await screen.findByText("Ningún cambio coincide con la búsqueda.")).toBeInTheDocument();
  });

  it("tells an empty channel apart from no matches", async () => {
    renderAt("/p/acme/widgets");
    expect(await screen.findByText("Aún no hay cambios en este canal.")).toBeInTheDocument();
  });

  it("shows the review summary without expanding the thread", async () => {
    renderAt("/p/duelo");
    const [first] = await screen.findAllByRole("list", { name: "Resumen de reviews" });
    expect(within(first).getByText("1 completada")).toBeInTheDocument();
    expect(within(first).getByText("1 en curso")).toBeInTheDocument();
  });
});

describe("channel threads", () => {
  it("expands replies with the keyboard and toggles aria-expanded", async () => {
    renderAt("/p/duelo");
    const [toggle] = await screen.findAllByRole("button", { name: "Ver respuestas" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    toggle.focus();
    await userEvent.keyboard("{Enter}");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getAllByText("Claude").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Codex").length).toBeGreaterThan(0);
  });

  it("filters by kind", async () => {
    renderAt("/p/duelo");
    // Four commits (two of them undone) and one PR.
    expect(await screen.findAllByRole("button", { name: "Ver respuestas" })).toHaveLength(5);
    await userEvent.click(screen.getByRole("button", { name: "PRs" }));
    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: "Ver respuestas" })).toHaveLength(1),
    );
  });
});

describe("review states", () => {
  it("shows thinking indicator and beam for a running review", async () => {
    setReducedMotion(false);
    const { container } = renderAt("/p/duelo/changes/c1");
    expect(await screen.findByText("Codex está revisando…")).toBeInTheDocument();
    expect(screen.getAllByText("En curso").length).toBeGreaterThan(0);
    expect(container.querySelector('[data-status="running"]')).not.toBeNull();
    expect(screen.getByText("Completada")).toBeInTheDocument();
  });

  it("shows failed state as text without thinking indicator", async () => {
    renderAt("/p/duelo/changes/c2");
    expect(await screen.findByText("Fallida")).toBeInTheDocument();
    expect(screen.queryByText(/está revisando/)).toBeNull();
  });

  it("falls back to a static indicator with reduced motion", async () => {
    setReducedMotion(true);
    const { container } = renderAt("/p/duelo/changes/c1");
    expect(await screen.findByText("Codex está revisando…")).toBeInTheDocument();
    expect(container.querySelector("canvas")).toBeNull();
    expect(container.querySelector("[data-beam-bloom]")).toBeNull();
  });
});

describe("other screens", () => {
  it("renders the change detail with diff and both reviews", async () => {
    renderAt("/p/duelo/changes/c1");
    expect(await screen.findByLabelText("Diff")).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(2);
  });

  it("numbers diff lines and marks additions and deletions", async () => {
    renderAt("/p/duelo/changes/c1");
    const diff = await screen.findByRole("table", { name: "Diff" });
    expect(within(diff).getByText("src/ingest.py")).toBeInTheDocument();
    expect(within(diff).getAllByText(/^\+ /).length).toBeGreaterThan(0);
    expect(diff.querySelectorAll("tr.del").length).toBeGreaterThan(0);
    expect(diff.querySelector("tr.add td.ln:nth-child(2)")?.textContent).toBe("1");
  });

  it("warns only when the diff is truncated", async () => {
    const { unmount } = renderAt("/p/duelo/changes/c1");
    await screen.findByRole("table", { name: "Diff" });
    expect(screen.queryByRole("note")).toBeNull();
    unmount();
    renderAt("/p/duelo/changes/c2");
    expect(await screen.findByRole("note")).toHaveTextContent("truncado");
  });

  it("keeps stats values as text and hides the bars from assistive tech", async () => {
    const { container } = renderAt("/stats");
    expect(await screen.findByRole("row", { name: /Claude/ })).toHaveTextContent("42 s");
    expect(screen.getByRole("row", { name: /Claude/ })).toHaveTextContent("4,1");
    const meters = container.querySelectorAll(".meter");
    expect(meters.length).toBe(4);
    for (const m of meters) expect(m).toHaveAttribute("aria-hidden", "true");
  });

  it("renders stats rows per agent", async () => {
    renderAt("/stats");
    expect(await screen.findByRole("row", { name: /Claude/ })).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Codex/ })).toBeInTheDocument();
  });

  it("renders settings", async () => {
    renderAt("/settings");
    expect(screen.getByText("Voto ciego")).toBeInTheDocument();
    expect(await screen.findByText("Postgres")).toBeInTheDocument();
  });
});

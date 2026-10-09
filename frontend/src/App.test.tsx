import { render, screen, within } from "@testing-library/react";
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
  it("redirects / to the first project channel and marks it active", () => {
    renderAt("/");
    expect(screen.getByRole("heading", { name: "#duelo" })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Principal" });
    expect(within(nav).getByRole("link", { name: /duelo/ })).toHaveClass("active");
  });

  it("navigates to stats and settings from the sidebar", async () => {
    renderAt("/");
    const nav = screen.getByRole("navigation", { name: "Principal" });
    await userEvent.click(within(nav).getByRole("link", { name: "Estadísticas" }));
    expect(screen.getByRole("heading", { name: "Estadísticas" })).toBeInTheDocument();
    await userEvent.click(within(nav).getByRole("link", { name: "Ajustes" }));
    expect(screen.getByRole("heading", { name: "Ajustes" })).toBeInTheDocument();
  });

  it("reaches interactive controls in order with Tab", async () => {
    renderAt("/p/duelo");
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "Menú" })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("link", { name: /duelo/ })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("link", { name: /demo-api/ })).toHaveFocus();
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
    await userEvent.type(screen.getByRole("searchbox", { name: "Buscar cambios" }), "9BE0");
    expect(screen.getAllByRole("button", { name: "Ver respuestas" })).toHaveLength(1);
    expect(screen.getByText("feat: exponer ingesta de commits")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Commits" }));
    expect(screen.getByText("Ningún cambio coincide con la búsqueda.")).toBeInTheDocument();
  });

  it("tells an empty channel apart from no matches", () => {
    renderAt("/p/demo-api");
    expect(screen.getByText("Aún no hay cambios en este canal.")).toBeInTheDocument();
  });

  it("shows the review summary without expanding the thread", () => {
    renderAt("/p/duelo");
    const [first] = screen.getAllByRole("list", { name: "Resumen de reviews" });
    expect(within(first).getByText("1 completada")).toBeInTheDocument();
    expect(within(first).getByText("1 en curso")).toBeInTheDocument();
  });
});

describe("channel threads", () => {
  it("expands replies with the keyboard and toggles aria-expanded", async () => {
    renderAt("/p/duelo");
    const [toggle] = screen.getAllByRole("button", { name: "Ver respuestas" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    toggle.focus();
    await userEvent.keyboard("{Enter}");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getAllByText("Claude").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Codex").length).toBeGreaterThan(0);
  });

  it("filters by kind", async () => {
    renderAt("/p/duelo");
    expect(screen.getAllByRole("button", { name: "Ver respuestas" })).toHaveLength(2);
    await userEvent.click(screen.getByRole("button", { name: "PRs" }));
    expect(screen.getAllByRole("button", { name: "Ver respuestas" })).toHaveLength(1);
  });
});

describe("review states", () => {
  it("shows thinking indicator and beam for a running review", () => {
    setReducedMotion(false);
    const { container } = renderAt("/p/duelo/changes/c1");
    expect(screen.getByText("En curso")).toBeInTheDocument();
    expect(screen.getByText("Codex está revisando…")).toBeInTheDocument();
    expect(container.querySelector('[data-status="running"]')).not.toBeNull();
    expect(screen.getByText("Completada")).toBeInTheDocument();
  });

  it("shows failed state as text without thinking indicator", () => {
    renderAt("/p/duelo/changes/c2");
    expect(screen.getByText("Fallida")).toBeInTheDocument();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("falls back to a static indicator with reduced motion", () => {
    setReducedMotion(true);
    const { container } = renderAt("/p/duelo/changes/c1");
    expect(screen.getByText("Codex está revisando…")).toBeInTheDocument();
    expect(container.querySelector("canvas")).toBeNull();
    expect(container.querySelector("[data-beam-bloom]")).toBeNull();
  });
});

describe("other screens", () => {
  it("renders the change detail with diff and both reviews", () => {
    renderAt("/p/duelo/changes/c1");
    expect(screen.getByLabelText("Diff")).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(2);
  });

  it("numbers diff lines and marks additions and deletions", () => {
    renderAt("/p/duelo/changes/c1");
    const diff = screen.getByRole("table", { name: "Diff" });
    expect(within(diff).getByText("src/ingest.py")).toBeInTheDocument();
    expect(within(diff).getAllByText(/^\+ /).length).toBeGreaterThan(0);
    expect(diff.querySelectorAll("tr.del").length).toBeGreaterThan(0);
    expect(diff.querySelector("tr.add td.ln:nth-child(2)")?.textContent).toBe("1");
  });

  it("warns only when the diff is truncated", () => {
    const { unmount } = renderAt("/p/duelo/changes/c1");
    expect(screen.queryByRole("note")).toBeNull();
    unmount();
    renderAt("/p/duelo/changes/c2");
    expect(screen.getByRole("note")).toHaveTextContent("truncado");
  });

  it("keeps stats values as text and hides the bars from assistive tech", () => {
    const { container } = renderAt("/stats");
    expect(screen.getByRole("row", { name: /Claude/ })).toHaveTextContent("68%");
    const meters = container.querySelectorAll(".meter");
    expect(meters.length).toBe(6);
    for (const m of meters) expect(m).toHaveAttribute("aria-hidden", "true");
  });

  it("renders stats rows per agent", () => {
    renderAt("/stats");
    expect(screen.getByRole("row", { name: /Claude/ })).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Codex/ })).toBeInTheDocument();
  });

  it("renders settings", () => {
    renderAt("/settings");
    expect(screen.getByText("Voto ciego")).toBeInTheDocument();
  });
});

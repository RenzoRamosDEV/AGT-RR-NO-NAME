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
    expect(screen.getByRole("heading", { name: "#review-arena" })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Principal" });
    expect(within(nav).getByRole("link", { name: /review-arena/ })).toHaveClass("active");
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
    renderAt("/p/review-arena");
    await userEvent.tab();
    expect(screen.getByRole("link", { name: /review-arena/ })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("link", { name: /demo-api/ })).toHaveFocus();
  });
});

describe("channel threads", () => {
  it("expands replies with the keyboard and toggles aria-expanded", async () => {
    renderAt("/p/review-arena");
    const [toggle] = screen.getAllByRole("button", { name: "Ver respuestas" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    toggle.focus();
    await userEvent.keyboard("{Enter}");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getAllByText("Claude").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Codex").length).toBeGreaterThan(0);
  });

  it("filters by kind", async () => {
    renderAt("/p/review-arena");
    expect(screen.getAllByRole("button", { name: "Ver respuestas" })).toHaveLength(2);
    await userEvent.click(screen.getByRole("button", { name: "PRs" }));
    expect(screen.getAllByRole("button", { name: "Ver respuestas" })).toHaveLength(1);
  });
});

describe("review states", () => {
  it("shows thinking indicator and beam for a running review", () => {
    setReducedMotion(false);
    const { container } = renderAt("/p/review-arena/changes/c1");
    expect(screen.getByText("En curso")).toBeInTheDocument();
    expect(screen.getByText("Codex está revisando…")).toBeInTheDocument();
    expect(container.querySelector('[data-status="running"]')).not.toBeNull();
    expect(screen.getByText("Completada")).toBeInTheDocument();
  });

  it("shows failed state as text without thinking indicator", () => {
    renderAt("/p/review-arena/changes/c2");
    expect(screen.getByText("Fallida")).toBeInTheDocument();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("falls back to a static indicator with reduced motion", () => {
    setReducedMotion(true);
    const { container } = renderAt("/p/review-arena/changes/c1");
    expect(screen.getByText("Codex está revisando…")).toBeInTheDocument();
    expect(container.querySelector("canvas")).toBeNull();
    expect(container.querySelector("[data-beam-bloom]")).toBeNull();
  });
});

describe("other screens", () => {
  it("renders the change detail with diff and both reviews", () => {
    renderAt("/p/review-arena/changes/c1");
    expect(screen.getByLabelText("Diff")).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(2);
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

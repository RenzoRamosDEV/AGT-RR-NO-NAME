import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { resetCollapsibleMemory } from "../../components/Collapsible";
import { makeFinding, makeReview } from "../../test/fixtures";
import { FindingsPanel } from "./FindingsPanel";

afterEach(resetCollapsibleMemory);

const reviews = () => [
  makeReview({
    id: "a",
    agent: "claude",
    findings: [
      makeFinding({ severity: "bug", file: "a.py", line: 3, message: "grave" }),
      makeFinding({ severity: "nit", file: "a.py", line: 9, message: "detalle uno" }),
      makeFinding({ severity: "nit", file: "N/A", line: 0, message: "detalle suelto" }),
    ],
  }),
  makeReview({
    id: "b",
    agent: "codex",
    findings: [makeFinding({ severity: "risk", file: "b.py", line: 1, message: "medio" })],
  }),
];

describe("FindingsPanel", () => {
  it("renders nothing without findings", () => {
    const { container } = render(<FindingsPanel reviews={[makeReview({ findings: [] })]} />);
    expect(container.innerHTML).toBe("");
  });

  it("counts the findings and each severity, most serious first", () => {
    render(<FindingsPanel reviews={reviews()} />);
    expect(screen.getByRole("heading", { name: "Hallazgos" })).toBeInTheDocument();
    const filters = screen.getByRole("group", { name: "Filtrar hallazgos por severidad" });
    const buttons = within(filters).getAllByRole("button");
    expect(buttons.map((b) => b.textContent?.replace(/\s+/g, " ").trim())).toEqual([
      "Todos 4",
      "Bug 1",
      "Riesgo 1",
      "Detalle 2",
    ]);
  });

  it("starts with every finding shown and «Todos» pressed", () => {
    render(<FindingsPanel reviews={reviews()} />);
    expect(screen.getByRole("button", { name: /^Todos/ })).toHaveAttribute("aria-pressed", "true");
    for (const text of ["grave", "medio", "detalle uno", "detalle suelto"]) {
      expect(screen.getByText(text)).toBeInTheDocument();
    }
  });

  it("filters by a severity and marks its button as pressed", async () => {
    const user = userEvent.setup();
    render(<FindingsPanel reviews={reviews()} />);
    await user.click(screen.getByRole("button", { name: /^Detalle/ }));
    expect(screen.getByRole("button", { name: /^Detalle/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: /^Todos/ })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByText("detalle uno")).toBeInTheDocument();
    expect(screen.getByText("detalle suelto")).toBeInTheDocument();
    expect(screen.queryByText("grave")).toBeNull();
    expect(screen.queryByText("medio")).toBeNull();
  });

  it("drops the groups the filter empties", async () => {
    const user = userEvent.setup();
    render(<FindingsPanel reviews={reviews()} />);
    await user.click(screen.getByRole("button", { name: /^Riesgo/ }));
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
      "b.py",
    ]);
  });

  it("pressing the active severity again, or «Todos», shows everything", async () => {
    const user = userEvent.setup();
    render(<FindingsPanel reviews={reviews()} />);
    await user.click(screen.getByRole("button", { name: /^Bug/ }));
    await user.click(screen.getByRole("button", { name: /^Bug/ }));
    expect(screen.getByText("medio")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^Bug/ }));
    await user.click(screen.getByRole("button", { name: /^Todos/ }));
    expect(screen.getByText("detalle uno")).toBeInTheDocument();
  });

  it("groups by file and puts the unlocated findings last, under «Sin archivo»", () => {
    render(<FindingsPanel reviews={reviews()} />);
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
      "a.py",
      "b.py",
      "Sin archivo",
    ]);
    const last = screen.getByRole("heading", { name: "Sin archivo" }).parentElement as HTMLElement;
    expect(within(last).queryByText(/N\/A|L0/)).toBeNull();
  });

  it("shows which agent found each one, with its avatar", () => {
    const { container } = render(<FindingsPanel reviews={reviews()} />);
    expect(screen.getAllByText("Claude").length).toBeGreaterThan(0);
    expect(screen.getByText("Codex")).toBeInTheDocument();
    expect(container.querySelectorAll(".finding-agent .avatar img").length).toBe(4);
  });

  it("lets the filter go away on its own when a refresh drops that severity", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<FindingsPanel reviews={reviews()} />);
    await user.click(screen.getByRole("button", { name: /^Riesgo/ }));
    rerender(<FindingsPanel reviews={[reviews()[0] as ReturnType<typeof reviews>[number]]} />);
    // The panel must not be left empty by a filter nobody can see any more.
    expect(screen.getByText("grave")).toBeInTheDocument();
  });

  // Regresión: el sondeo entrega objetos nuevos cada vez; un hallazgo abierto no debe plegarse.
  it("keeps a long finding open across refreshes that hand it new objects", async () => {
    const user = userEvent.setup();
    const long = () => [
      makeReview({
        id: "stable",
        findings: [makeFinding({ severity: "bug", message: "texto largo ".repeat(40) })],
      }),
    ];
    const { rerender } = render(<FindingsPanel reviews={long()} />);
    await user.click(screen.getByRole("button", { name: "Ver más" }));
    rerender(<FindingsPanel reviews={long()} />);
    expect(screen.getByRole("button", { name: "Ver menos" })).toBeInTheDocument();
  });
});

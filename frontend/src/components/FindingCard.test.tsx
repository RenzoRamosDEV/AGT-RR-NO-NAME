import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { makeFinding } from "../test/fixtures";
import { resetCollapsibleMemory } from "./Collapsible";
import { FindingCard } from "./FindingCard";

const copyText = vi.hoisted(() => vi.fn(async () => true));
vi.mock("../lib/clipboard", () => ({ copyText }));

afterEach(() => {
  resetCollapsibleMemory();
  copyText.mockClear();
});

describe("FindingCard", () => {
  it("shows the severity in Spanish with its color family", () => {
    const { container, rerender } = render(
      <FindingCard id="f" finding={makeFinding({ severity: "bug" })} />,
    );
    expect(screen.getByText("Bug")).toBeInTheDocument();
    expect(container.firstElementChild).toHaveAttribute("data-level", "danger");
    rerender(<FindingCard id="f" finding={makeFinding({ severity: "risk" })} />);
    expect(screen.getByText("Riesgo")).toBeInTheDocument();
    expect(container.firstElementChild).toHaveAttribute("data-level", "warning");
    rerender(<FindingCard id="f" finding={makeFinding({ severity: "improvement" })} />);
    expect(container.firstElementChild).toHaveAttribute("data-level", "info");
    rerender(<FindingCard id="f" finding={makeFinding({ severity: "nit" })} />);
    expect(container.firstElementChild).toHaveAttribute("data-level", "neutral");
  });

  it("shows `archivo:línea` as a chip that copies it", async () => {
    const user = userEvent.setup();
    render(<FindingCard id="f" finding={makeFinding({ file: "src/app.py", line: 42 })} />);
    expect(screen.getByText("src/app.py:42")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Copiar ubicación src\/app\.py:42/ }));
    expect(copyText).toHaveBeenCalledWith("src/app.py:42");
    expect(await screen.findByText("Copiado")).toBeInTheDocument();
  });

  it("shows only the file when there is no line", () => {
    render(<FindingCard id="f" finding={makeFinding({ file: "README.md", line: 0 })} />);
    expect(screen.getByText("README.md")).toBeInTheDocument();
    expect(screen.queryByText(/README\.md:/)).toBeNull();
  });

  // Regresión: con el agente de prueba llegaban `N/A` y `L0`.
  it("shows no location chip, N/A or L0 when the finding has no file", () => {
    render(<FindingCard id="f" finding={makeFinding({ file: "N/A", line: 0 })} />);
    expect(screen.queryByRole("button", { name: /Copiar/ })).toBeNull();
    expect(screen.queryByText(/N\/A|L0/)).toBeNull();
  });

  it("under a heading that names the file, shows only the line", () => {
    render(
      <FindingCard id="f" finding={makeFinding({ file: "a.py", line: 7 })} showFile={false} />,
    );
    expect(screen.getByText("L7")).toBeInTheDocument();
    expect(screen.queryByText(/a\.py/)).toBeNull();
  });

  it("formats the message: code in line, never literal backticks", () => {
    const { container } = render(
      <FindingCard
        id="f"
        finding={makeFinding({ message: "Revisa `hook.env` y **rota** la clave" })}
      />,
    );
    expect(container.querySelector("code")).toHaveTextContent("hook.env");
    expect(container.querySelector("strong")).toHaveTextContent("rota");
    expect(container).not.toHaveTextContent("`");
  });

  it("separates the advice after a label into its own block", () => {
    const { container } = render(
      <FindingCard
        id="f"
        finding={makeFinding({
          message: "La clave queda en el repo. Arreglo: cárgala del entorno.",
        })}
      />,
    );
    const reco = container.querySelector(".finding-reco") as HTMLElement;
    expect(within(reco).getByText("Arreglo sugerido")).toBeInTheDocument();
    expect(reco).toHaveTextContent("cárgala del entorno.");
    // The problem and the advice are not repeated.
    expect(container.querySelector(".finding-text")).toHaveTextContent(
      "La clave queda en el repo.",
    );
    expect(container.querySelector(".finding-text")).not.toHaveTextContent("cárgala");
  });

  it("has no advice block without a label", () => {
    const { container } = render(<FindingCard id="f" finding={makeFinding()} />);
    expect(container.querySelector(".finding-reco")).toBeNull();
  });

  it("names the agent when findings of several agents are mixed", () => {
    render(<FindingCard id="f" finding={makeFinding()} agent="codex" />);
    expect(screen.getByText("Codex")).toBeInTheDocument();
  });

  it("folds a long message", () => {
    render(<FindingCard id="long" finding={makeFinding({ message: "palabra ".repeat(80) })} />);
    expect(screen.getByRole("button", { name: "Ver más" })).toBeInTheDocument();
  });

  it("does not run HTML from the message", () => {
    const { container } = render(
      <FindingCard id="f" finding={makeFinding({ message: "<img src=x onerror=alert(1)>" })} />,
    );
    expect(container.querySelector("img")).toBeNull();
  });
});

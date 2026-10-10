import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import {
  Collapsible,
  FINDING_LIMIT,
  SUMMARY_LIMIT,
  isLong,
  resetCollapsibleMemory,
} from "./Collapsible";

afterEach(resetCollapsibleMemory);

describe("isLong", () => {
  it("is decided by characters or by lines", () => {
    expect(isLong("a".repeat(SUMMARY_LIMIT.chars), SUMMARY_LIMIT)).toBe(false);
    expect(isLong("a".repeat(SUMMARY_LIMIT.chars + 1), SUMMARY_LIMIT)).toBe(true);
    expect(isLong("x\n".repeat(SUMMARY_LIMIT.lines), SUMMARY_LIMIT)).toBe(true);
    expect(isLong("x\n".repeat(SUMMARY_LIMIT.lines - 1), SUMMARY_LIMIT)).toBe(false);
  });

  it("is stricter for a finding than for a summary", () => {
    const text = "a".repeat(FINDING_LIMIT.chars + 1);
    expect(isLong(text, FINDING_LIMIT)).toBe(true);
    expect(isLong(text, SUMMARY_LIMIT)).toBe(false);
  });
});

describe("Collapsible", () => {
  it("renders short content as it is, with no button", () => {
    render(
      <Collapsible id="s" long={false}>
        <p>corto</p>
      </Collapsible>,
    );
    expect(screen.getByText("corto")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("folds long content with an accessible «Ver más» button", () => {
    const { container } = render(
      <Collapsible id="a" long>
        <p>largo</p>
      </Collapsible>,
    );
    const button = screen.getByRole("button", { name: "Ver más" });
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(container.querySelector(".collapsible")).toHaveAttribute("data-open", "false");
    // The button controls the folded region.
    const region = container.querySelector(".collapsible-body") as HTMLElement;
    expect(button.getAttribute("aria-controls")).toBe(region.id);
  });

  it("opens and folds again", async () => {
    const user = userEvent.setup();
    render(
      <Collapsible id="b" long>
        <p>largo</p>
      </Collapsible>,
    );
    await user.click(screen.getByRole("button", { name: "Ver más" }));
    expect(screen.getByRole("button", { name: "Ver menos" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    await user.click(screen.getByRole("button", { name: "Ver menos" }));
    expect(screen.getByRole("button", { name: "Ver más" })).toBeInTheDocument();
  });

  it("stays open when the page refreshes itself and re-renders it", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <Collapsible id="c" long>
        <p>versión 1</p>
      </Collapsible>,
    );
    await user.click(screen.getByRole("button", { name: "Ver más" }));
    rerender(
      <Collapsible id="c" long>
        <p>versión 2 con el mismo id</p>
      </Collapsible>,
    );
    expect(screen.getByRole("button", { name: "Ver menos" })).toBeInTheDocument();
    expect(screen.getByText("versión 2 con el mismo id")).toBeInTheDocument();
  });

  // Regresión: el sondeo vuelve a montar listas enteras; un texto abierto no debe volver a plegarse.
  it("stays open when the component is mounted again", async () => {
    const user = userEvent.setup();
    const first = render(
      <Collapsible id="d" long>
        <p>x</p>
      </Collapsible>,
    );
    await user.click(screen.getByRole("button", { name: "Ver más" }));
    first.unmount();
    render(
      <Collapsible id="d" long>
        <p>x</p>
      </Collapsible>,
    );
    expect(screen.getByRole("button", { name: "Ver menos" })).toBeInTheDocument();
  });

  it("remembers each text on its own id", async () => {
    const user = userEvent.setup();
    render(
      <>
        <Collapsible id="uno" long>
          <p>uno</p>
        </Collapsible>
        <Collapsible id="dos" long>
          <p>dos</p>
        </Collapsible>
      </>,
    );
    await user.click(screen.getAllByRole("button", { name: "Ver más" })[0] as HTMLElement);
    expect(screen.getAllByRole("button")).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Ver menos" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ver más" })).toBeInTheDocument();
  });
});

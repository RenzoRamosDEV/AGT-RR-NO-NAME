import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ACTIVITY_STATE, Busy } from "./Busy";

// The real orb paints on a canvas, which jsdom lacks: this stand-in records what it was asked for.
vi.mock("thinking-orbs", () => ({
  ThinkingOrb: (props: { state: string; size: number; theme: string }) => (
    <canvas data-orb data-state={props.state} data-size={props.size} data-theme={props.theme} />
  ),
}));

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

describe("Busy", () => {
  it.each([
    ["load", "searching"],
    ["more", "working"],
    ["agent", "working"],
    ["retry", "solving"],
    ["connect", "connecting"],
  ] as const)("a %s activity draws the %s orb, 20 px, on the dark theme", (activity, state) => {
    const { container } = render(<Busy activity={activity} label="Trabajando…" />);
    const orb = container.querySelector("canvas[data-orb]");
    expect(orb).toHaveAttribute("data-state", state);
    expect(orb).toHaveAttribute("data-size", "20");
    expect(orb).toHaveAttribute("data-theme", "dark");
    expect(ACTIVITY_STATE[activity]).toBe(state);
  });

  it("announces its label as a polite status region and keeps the orb decorative", () => {
    const { container } = render(<Busy activity="load" label="Cargando cambios…" />);
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("Cargando cambios…");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(container.querySelector(".busy-orb")).toHaveAttribute("aria-hidden", "true");
  });

  it("in line form is a plain span, so a button does not nest a live region", () => {
    const { container } = render(
      <button type="button" disabled>
        <Busy activity="retry" label="Reintentando…" inline />
      </button>,
    );
    expect(screen.queryByRole("status")).toBeNull();
    expect(screen.getByRole("button", { name: "Reintentando…" })).toBeDisabled();
    expect(container.querySelector("canvas[data-orb]")).toHaveAttribute("data-state", "solving");
  });

  it("mounts no canvas under reduced motion but keeps the label and the same 20 px slot", () => {
    setReducedMotion(true);
    const { container } = render(<Busy activity="load" label="Cargando cambios…" />);
    expect(container.querySelector("canvas")).toBeNull();
    expect(screen.getByRole("status")).toHaveTextContent("Cargando cambios…");
    expect(container.querySelector(".busy-orb")).toHaveTextContent("…");
  });
});

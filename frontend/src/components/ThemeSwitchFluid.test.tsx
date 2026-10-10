import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetThemeForTests } from "../lib/theme";
import { ThemeSwitch } from "./ThemeSwitch";

const SEGMENT = 40;

/** jsdom has no layout: give every segment a width and a position so the indicator can be measured. */
function stubLayout() {
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(SEGMENT);
  vi.spyOn(HTMLElement.prototype, "offsetLeft", "get").mockImplementation(function (
    this: HTMLElement,
  ) {
    const siblings = [...(this.parentElement?.querySelectorAll("button.segment") ?? [])];
    return siblings.indexOf(this as HTMLButtonElement) * SEGMENT;
  });
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

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  resetThemeForTests();
});
afterEach(() => vi.restoreAllMocks());

describe("ThemeSwitch with the liquid indicator (liquid-gooey)", () => {
  it("is usable at once as a plain control and gets the liquid indicator when the chunk arrives", async () => {
    stubLayout();
    const { container } = render(<ThemeSwitch compact />);
    // First paint: the buttons are already there and work, with no liquid layer yet.
    expect(screen.getByRole("button", { name: "Tema sistema" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await waitFor(() => expect(container.querySelector(".theme-liquid")).not.toBeNull());
    await waitFor(() => expect(container.querySelector("[data-fluid]")).not.toBeNull());
    const thumb = container.querySelector<HTMLElement>(".theme-thumb");
    expect(thumb).toHaveAttribute("aria-hidden", "true");
    expect(thumb?.style.width).toBe(`${SEGMENT}px`);
    expect(thumb?.style.transform).toBe("translateX(0px)");
  });

  it("slides the indicator to the chosen option while the buttons stay real, crisp buttons", async () => {
    stubLayout();
    const { container } = render(<ThemeSwitch compact />);
    await waitFor(() => expect(container.querySelector(".theme-thumb")).not.toBeNull());

    await userEvent.click(screen.getByRole("button", { name: "Tema oscuro" }));
    expect(screen.getByRole("button", { name: "Tema oscuro" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await waitFor(() =>
      expect(container.querySelector<HTMLElement>(".theme-thumb")?.style.transform).toBe(
        `translateX(${2 * SEGMENT}px)`,
      ),
    );
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
  });

  it("has no indicator at all under prefers-reduced-motion, and still switches the theme", async () => {
    stubLayout();
    setReducedMotion(true);
    const { container } = render(<ThemeSwitch compact />);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(container.querySelector(".theme-liquid")).toBeNull();
    expect(container.querySelector(".theme-thumb")).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "Tema claro" }));
    expect(screen.getByRole("button", { name: "Tema claro" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
  });
});

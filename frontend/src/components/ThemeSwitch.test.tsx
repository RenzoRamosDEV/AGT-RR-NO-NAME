import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { THEME_KEY, resetThemeForTests } from "../lib/theme";
import { ThemeSwitch } from "./ThemeSwitch";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  resetThemeForTests();
});

afterEach(() => vi.restoreAllMocks());

describe("ThemeSwitch", () => {
  it("offers System, Light and Dark as toggle buttons and marks the one in force", () => {
    render(<ThemeSwitch />);
    const group = screen.getByRole("group", { name: "Tema" });
    expect(group).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sistema" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Claro" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Oscuro" })).toHaveAttribute("aria-pressed", "false");
  });

  it("applies and remembers the choice", async () => {
    render(<ThemeSwitch />);
    await userEvent.click(screen.getByRole("button", { name: "Claro" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
    expect(localStorage.getItem(THEME_KEY)).toBe("light");
    expect(screen.getByRole("button", { name: "Claro" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Sistema" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );

    await userEvent.click(screen.getByRole("button", { name: "Oscuro" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(localStorage.getItem(THEME_KEY)).toBe("dark");
  });

  it("keeps two switches (header and Settings) in step", async () => {
    render(
      <>
        <ThemeSwitch compact />
        <ThemeSwitch />
      </>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Tema oscuro" }));
    expect(screen.getByRole("button", { name: "Oscuro" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("button", { name: "Claro" }));
    expect(screen.getByRole("button", { name: "Tema claro" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("the compact form shows icons only but every button keeps its full accessible name", () => {
    render(<ThemeSwitch compact />);
    for (const name of ["Tema sistema", "Tema claro", "Tema oscuro"]) {
      expect(screen.getByRole("button", { name })).toHaveTextContent("");
    }
  });
});

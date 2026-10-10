import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { act, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import App from "../App";
import { DataSourceProvider } from "../data/source";
import type { DataSource } from "../lib/api";
import { resetThemeForTests, setThemePreference } from "../lib/theme";
import { makeSource } from "../test/fixtures";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  resetThemeForTests();
});

afterEach(() => resetThemeForTests());

function renderApp(path: string, overrides: Partial<DataSource> = {}) {
  return render(
    <DataSourceProvider source={makeSource({ projects: async () => [], ...overrides })}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </DataSourceProvider>,
  );
}

const hero = () => document.querySelector<HTMLImageElement>("img.hero-img") as HTMLImageElement;

describe("the Duelo logo of the theme in force", () => {
  it("is the brand of the top bar, next to the name", async () => {
    setThemePreference("dark");
    renderApp("/");
    const brand = (await screen.findByRole("link", { name: "Duelo" })) as HTMLElement;
    expect(brand.querySelector("img.brand-logo")).toHaveAttribute("data-variant", "dark");
    expect(brand).toHaveTextContent("Duelo");
  });

  it("is the main picture of the empty state, one per theme", async () => {
    setThemePreference("dark");
    renderApp("/");
    await screen.findByText("Aún no hay proyectos vigilados.");
    expect(hero().getAttribute("src")).toContain("hero-dark");

    act(() => setThemePreference("light"));
    expect(hero().getAttribute("src")).toContain("hero-light");
  });

  it("is also the picture of the not-found pages", async () => {
    setThemePreference("light");
    renderApp("/no-existe");
    await screen.findByRole("heading", { name: "No encontrado" });
    expect(hero().getAttribute("src")).toContain("hero-light");
  });

  it("is the picture of a project that does not exist", async () => {
    setThemePreference("dark");
    renderApp("/p/acme/nada", {
      projects: async () => [{ slug: "acme/otro", name: "acme/otro" }],
      changes: async () => {
        const { ApiError } = await import("../lib/api");
        throw new ApiError("no existe", 404);
      },
    });
    await screen.findByRole("heading", { name: "Proyecto no encontrado" });
    expect(hero().getAttribute("src")).toContain("hero-dark");
  });
});

describe("the tab icons", () => {
  // Vitest runs from `frontend/`, so the files are read from there.
  const html = readFileSync(resolve(process.cwd(), "index.html"), "utf8");

  it("declares one icon per system color scheme and the Apple icon", () => {
    expect(html).toMatch(/favicon-dark-32\.png[\s\S]*?prefers-color-scheme: dark/);
    expect(html).toMatch(/favicon-light-32\.png[\s\S]*?prefers-color-scheme: light/);
    expect(html).toContain('rel="apple-touch-icon"');
  });

  it("no longer points at the old crossed-blades icon", () => {
    expect(html).not.toContain("favicon.svg");
    expect(html).not.toContain("image/svg+xml");
  });

  it("ships every icon file it declares", () => {
    for (const file of ["favicon-dark-32.png", "favicon-light-32.png", "apple-touch-icon.png"]) {
      expect(() => readFileSync(resolve(process.cwd(), "public", file))).not.toThrow();
    }
  });
});

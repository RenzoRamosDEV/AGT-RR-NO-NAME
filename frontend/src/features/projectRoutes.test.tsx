import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { DataSourceProvider } from "../data/source";
import type { DataSource } from "../lib/api";
import { makeChange, makeSource } from "../test/fixtures";

const SLUG = "acme/widgets";

function renderWith(source: Partial<DataSource>, path: string) {
  const full = makeSource({
    projects: async () => [{ slug: SLUG, name: SLUG }],
    ...source,
  });
  return render(
    <DataSourceProvider source={full}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </DataSourceProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

/**
 * Regresión: los slugs reales del backend son `owner/repo`, pero las rutas eran `p/:slug`, que no
 * casa con una barra. Con la API real `/` redirigía a `/p/acme/widgets`, sin ruta, y la página
 * quedaba en blanco. Los mocks (slug sin barra) lo ocultaban. Hallado al probar el frontend
 * contra el backend real en la ronda 4.
 */
describe("project routes with an owner/repo slug (regression)", () => {
  it("redirects / to the channel of the first project", async () => {
    const changes = vi.fn(async () => ({
      items: [makeChange({ id: "c1", title: "hola" })],
      nextCursor: null,
    }));
    renderWith({ changes }, "/");
    expect(await screen.findByText("hola")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: `#${SLUG}` })).toBeInTheDocument();
    expect(changes).toHaveBeenCalledWith(SLUG, expect.anything());
  });

  it("opens the change detail and links back to the channel", async () => {
    const change = vi.fn(async (id: string) => makeChange({ id, title: "detalle" }));
    renderWith({ change }, `/p/${SLUG}/changes/c1`);
    expect(await screen.findByRole("heading", { name: "detalle" })).toBeInTheDocument();
    expect(change).toHaveBeenCalledWith("c1");
    expect(screen.getByRole("link", { name: `#${SLUG}` })).toHaveAttribute("href", `/p/${SLUG}`);
  });

  it("navigates from a card to its detail and from the sidebar to the channel", async () => {
    const item = makeChange({ id: "c9", title: "abrir" });
    renderWith(
      {
        changes: async () => ({ items: [item], nextCursor: null }),
        change: async () => item,
      },
      `/p/${SLUG}`,
    );
    const card = await screen.findByRole("link", { name: "abrir" });
    expect(card).toHaveAttribute("href", `/p/${SLUG}/changes/c9`);
    await userEvent.click(card);
    expect(await screen.findByRole("link", { name: `#${SLUG}` })).toBeInTheDocument();
  });
});

describe("not found", () => {
  it("shows a visible page for an unknown route", async () => {
    renderWith({}, "/nada");
    expect(await screen.findByRole("heading", { name: "No encontrado" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Volver al inicio" })).toHaveAttribute("href", "/");
  });

  it("shows it for /p without a project", async () => {
    renderWith({}, "/p");
    expect(await screen.findByRole("heading", { name: "No encontrado" })).toBeInTheDocument();
  });
});

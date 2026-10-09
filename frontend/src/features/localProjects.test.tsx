import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { DataSourceProvider } from "../data/source";
import { ApiError, type DataSource, type ProjectRef } from "../lib/api";
import { clearIngestToken, getIngestToken, setIngestToken } from "../lib/ingestToken";
import { makeSource } from "../test/fixtures";

const NEW_PROJECT: ProjectRef = {
  slug: "acme/widgets",
  name: "acme/widgets",
  path: "/home/me/acme/widgets",
  hooksInstalled: true,
  github: false,
};

/** A source whose project list is stateful, like the server's. */
function projectSource(initial: ProjectRef[], overrides: Partial<DataSource> = {}) {
  let list = [...initial];
  return makeSource({
    projects: async () => list.map((p) => ({ ...p })),
    addProject: vi.fn(async (path: string) => {
      const project = { ...NEW_PROJECT, path };
      list = [...list, project];
      return project;
    }),
    removeProject: vi.fn(async (slug: string) => {
      list = list.filter((p) => p.slug !== slug);
    }),
    ...overrides,
  });
}

function renderApp(source: DataSource, path = "/") {
  return render(
    <DataSourceProvider source={source}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </DataSourceProvider>,
  );
}

const sidebar = () => within(screen.getByRole("navigation", { name: "Principal" }));
const openFromSidebar = async () => {
  await userEvent.click(await sidebar().findByRole("button", { name: "Añadir proyecto" }));
  return screen.findByRole("dialog", { name: "Añadir proyecto" });
};

beforeEach(clearIngestToken);
afterEach(() => vi.restoreAllMocks());

describe("add project dialog", () => {
  it("opens an accessible dialog focused on the path with the hooks explained", async () => {
    renderApp(projectSource([]));
    const dialog = await openFromSidebar();
    expect(dialog).toHaveAttribute("aria-modal", "true");
    const path = within(dialog).getByLabelText("Ruta del repositorio");
    expect(path).toHaveFocus();
    expect(dialog).toHaveTextContent("post-commit");
    expect(dialog).toHaveTextContent("pre-push");
    expect(within(dialog).getByLabelText("Token de ingesta")).toHaveAttribute("type", "password");
  });

  it("keeps Tab inside the dialog in both directions", async () => {
    renderApp(projectSource([]));
    const dialog = await openFromSidebar();
    const path = within(dialog).getByLabelText("Ruta del repositorio");
    const add = within(dialog).getByRole("button", { name: "Añadir" });

    await userEvent.tab({ shift: true });
    expect(add).toHaveFocus();
    await userEvent.tab();
    expect(path).toHaveFocus();
    await userEvent.tab();
    expect(within(dialog).getByLabelText("Token de ingesta")).toHaveFocus();
  });

  it("closes on Escape or Cancel and gives the focus back to the button that opened it", async () => {
    renderApp(projectSource([]));
    const opener = await sidebar().findByRole("button", { name: "Añadir proyecto" });
    await openFromSidebar();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(opener).toHaveFocus();

    await openFromSidebar();
    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(opener).toHaveFocus();
  });

  it("rejects a relative path without calling the API", async () => {
    const source = projectSource([]);
    renderApp(source);
    const dialog = await openFromSidebar();
    await userEvent.type(within(dialog).getByLabelText("Ruta del repositorio"), "mi/repo");
    await userEvent.type(within(dialog).getByLabelText("Token de ingesta"), "tok");
    await userEvent.click(within(dialog).getByRole("button", { name: "Añadir" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("ruta absoluta");
    expect(source.addProject).not.toHaveBeenCalled();
  });

  it("asks for the token before calling the API", async () => {
    const source = projectSource([]);
    renderApp(source);
    const dialog = await openFromSidebar();
    await userEvent.type(within(dialog).getByLabelText("Ruta del repositorio"), "/home/me/repo");
    await userEvent.click(within(dialog).getByRole("button", { name: "Añadir" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("token de ingesta");
    expect(source.addProject).not.toHaveBeenCalled();
  });

  it("adds the project, lists it in the sidebar, selects it and never stores the token", async () => {
    const source = projectSource([]);
    renderApp(source);
    const dialog = await openFromSidebar();
    await userEvent.type(
      within(dialog).getByLabelText("Ruta del repositorio"),
      "  /home/me/acme/widgets  ",
    );
    await userEvent.type(within(dialog).getByLabelText("Token de ingesta"), "secret-token");
    await userEvent.click(within(dialog).getByRole("button", { name: "Añadir" }));

    expect(await screen.findByRole("heading", { name: "#acme/widgets" })).toBeInTheDocument();
    expect(source.addProject).toHaveBeenCalledWith("/home/me/acme/widgets", "secret-token");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(await sidebar().findByRole("link", { name: /acme\/widgets/ })).toHaveClass("active");
    expect(JSON.stringify({ ...localStorage })).not.toContain("secret-token");
    expect(JSON.stringify({ ...sessionStorage })).not.toContain("secret-token");
  });

  it.each([
    [404, "LOCAL_PROJECTS_ENABLED=true"],
    [409, "ya está añadido"],
    [422, "no es un repositorio git válido"],
    [401, "Token de ingesta no válido"],
  ])("explains an API %i", async (status, text) => {
    const source = projectSource([], {
      addProject: vi.fn(async () => {
        throw new ApiError("raw", status);
      }),
    });
    renderApp(source);
    const dialog = await openFromSidebar();
    await userEvent.type(within(dialog).getByLabelText("Ruta del repositorio"), "/home/me/repo");
    await userEvent.type(within(dialog).getByLabelText("Token de ingesta"), "tok");
    await userEvent.click(within(dialog).getByRole("button", { name: "Añadir" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(text);
    // Still open and editable so the user can fix it; only a 401 forgets the token.
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(getIngestToken()).toBe(status === 401 ? "" : "tok");
  });

  it("is offered from the empty state too", async () => {
    renderApp(projectSource([]));
    expect(await screen.findByText("Aún no hay proyectos vigilados.")).toBeInTheDocument();
    const main = within(screen.getByRole("main"));
    await userEvent.click(main.getByRole("button", { name: "Añadir proyecto" }));
    expect(await screen.findByRole("dialog", { name: "Añadir proyecto" })).toBeInTheDocument();
  });
});

describe("project settings", () => {
  const github: ProjectRef = { ...NEW_PROJECT, github: true };
  const plain: ProjectRef = {
    slug: "me/plain",
    name: "me/plain",
    path: "/home/me/plain",
    hooksInstalled: false,
    github: false,
  };

  const row = (name: string) =>
    within(screen.getByRole("main")).getByText(name, { selector: "strong" }).closest("li")!;

  it("lists each project with its path and the state of its hooks", async () => {
    renderApp(projectSource([github, plain]), "/settings");
    const first = within(
      await screen.findByText("acme/widgets", { selector: "strong" }).then((e) => e.closest("li")!),
    );
    expect(first.getByText("/home/me/acme/widgets")).toBeInTheDocument();
    expect(first.getByText("Hooks instalados")).toBeInTheDocument();
    const second = within(row("me/plain"));
    expect(second.getByText("Sin hooks")).toBeInTheDocument();
  });

  it("offers «Sincronizar PRs» only for GitHub projects and reports the counters", async () => {
    const syncPrs = vi.fn(async () => ({ synced: 2, created: 1 }));
    renderApp(projectSource([github, plain], { syncPrs }), "/settings");
    await screen.findByText("me/plain", { selector: "strong" });
    expect(within(row("me/plain")).queryByRole("button", { name: /Sincronizar/ })).toBeNull();

    await userEvent.click(
      within(row("acme/widgets")).getByRole("button", { name: /Sincronizar PRs/ }),
    );
    expect(within(row("acme/widgets")).getByRole("alert")).toHaveTextContent("token");
    expect(syncPrs).not.toHaveBeenCalled();

    setIngestToken("tok");
    await userEvent.click(
      within(row("acme/widgets")).getByRole("button", { name: /Sincronizar PRs/ }),
    );
    expect(
      await within(row("acme/widgets")).findByText("2 PRs sincronizadas (1 nueva)."),
    ).toBeInTheDocument();
    expect(syncPrs).toHaveBeenCalledWith("acme/widgets", "tok");
  });

  it("shows why a sync failed (503 brings the reason) and forgets the token on a 401", async () => {
    const syncPrs = vi
      .fn()
      .mockRejectedValueOnce(new ApiError("`gh` no está instalado.", 503))
      .mockRejectedValueOnce(new ApiError("x", 401));
    renderApp(projectSource([github], { syncPrs }), "/settings");
    setIngestToken("tok");
    const button = await screen.findByRole("button", { name: /Sincronizar PRs/ });
    await userEvent.click(button);
    expect(await within(row("acme/widgets")).findByRole("alert")).toHaveTextContent(
      "`gh` no está instalado.",
    );
    await userEvent.click(button);
    await waitFor(() => expect(getIngestToken()).toBe(""));
    expect(within(row("acme/widgets")).getByRole("alert")).toHaveTextContent(
      "Token de ingesta no válido",
    );
  });

  it("asks for an explicit confirmation before removing and warns that the history goes", async () => {
    const source = projectSource([github, plain]);
    renderApp(source, "/settings");
    setIngestToken("tok");
    await userEvent.click(
      await screen.findByRole("button", { name: "Quitar proyecto acme/widgets" }),
    );
    const dialog = await screen.findByRole("dialog", { name: "Quitar acme/widgets" });
    expect(dialog).toHaveTextContent("todo el historial");
    expect(dialog).toHaveTextContent("hooks de git");
    expect(within(dialog).getByRole("button", { name: "Cancelar" })).toHaveFocus();
    expect(source.removeProject).not.toHaveBeenCalled();

    await userEvent.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(source.removeProject).not.toHaveBeenCalled();
    expect(screen.getAllByText("acme/widgets", { selector: "strong" })).toHaveLength(1);
  });

  it("removes the project once confirmed and updates the list and the sidebar", async () => {
    const source = projectSource([github, plain]);
    renderApp(source, "/settings");
    setIngestToken("tok");
    await userEvent.click(
      await screen.findByRole("button", { name: "Quitar proyecto acme/widgets" }),
    );
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Quitar proyecto" }));

    expect(await screen.findByText("Proyecto acme/widgets quitado.")).toBeInTheDocument();
    expect(source.removeProject).toHaveBeenCalledWith("acme/widgets", "tok");
    await waitFor(() =>
      expect(screen.queryByText("acme/widgets", { selector: "strong" })).toBeNull(),
    );
    expect(sidebar().queryByRole("link", { name: /acme\/widgets/ })).toBeNull();
    expect(sidebar().getByRole("link", { name: /me\/plain/ })).toBeInTheDocument();
  });

  it("does not remove without a token and explains a 404", async () => {
    const removeProject = vi.fn().mockRejectedValue(new ApiError("x", 404));
    renderApp(projectSource([github], { removeProject }), "/settings");
    await userEvent.click(
      await screen.findByRole("button", { name: "Quitar proyecto acme/widgets" }),
    );
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Quitar proyecto" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("token de ingesta");
    expect(removeProject).not.toHaveBeenCalled();

    await userEvent.type(within(dialog).getByLabelText("Token de ingesta"), "tok");
    await userEvent.click(within(dialog).getByRole("button", { name: "Quitar proyecto" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("ya no existe");
  });
});

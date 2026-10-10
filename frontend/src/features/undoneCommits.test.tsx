import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

afterEach(() => vi.restoreAllMocks());

/** The row (`li`) of the change with that title. */
async function rowOf(title: string): Promise<HTMLElement> {
  const link = await screen.findByRole("link", { name: title });
  const row = link.closest("li");
  if (!row) throw new Error(`no row for ${title}`);
  return row;
}

const DISCARDED = "fix: ajustar el límite de peticiones por IP";
const REVERTED = "feat: filtros del canal en el servidor";
const REVERT = 'Revert "feat: filtros del canal en el servidor"';

describe("undone commits in the channel", () => {
  it("paints a discarded commit in amber and says so in the middle of its row", async () => {
    renderAt("/p/duelo");
    const row = await rowOf(DISCARDED);
    expect(row).toHaveAttribute("data-commit-state", "discarded");
    expect(within(row).getByText("COMMIT DESHECHO")).toBeInTheDocument();
    expect(within(row).getByText("Ya no está en la rama")).toBeInTheDocument();
    expect(within(row).getByRole("img", { name: "COMMIT DESHECHO" })).toBeInTheDocument();
  });

  it("says a reverted commit was reverted and by which commit", async () => {
    renderAt("/p/duelo");
    const row = await rowOf(REVERTED);
    expect(row).toHaveAttribute("data-commit-state", "reverted");
    expect(within(row).getByText("COMMIT REVERTIDO")).toBeInTheDocument();
    expect(within(row).getByText("Revertido por d93f0b4")).toBeInTheDocument();
  });

  it("leaves the commit that reverts it, and the other changes, as normal rows", async () => {
    renderAt("/p/duelo");
    for (const title of [REVERT, "fix: comparar el token de ingesta en tiempo constante"]) {
      const row = await rowOf(title);
      expect(row).not.toHaveAttribute("data-commit-state");
      expect(within(row).queryByText(/COMMIT (DESHECHO|REVERTIDO)/)).toBeNull();
    }
  });

  it("keeps the reviews: «Ver respuestas» still opens the thread of an undone commit", async () => {
    renderAt("/p/duelo");
    const row = await rowOf(DISCARDED);
    const toggle = within(row).getByRole("button", { name: "Ver respuestas" });
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(within(row).getAllByText("APP").length).toBeGreaterThan(0);
  });

  it("still counts an undone commit as a normal change in the review counters", async () => {
    renderAt("/p/duelo");
    await rowOf(DISCARDED);
    const count = document.querySelector(".list-count");
    // c3, c4 and c5 are completed, whatever happened to them afterwards.
    expect(count).toHaveTextContent("3 completados");
    expect(count).toHaveTextContent("1 deshecho · 1 revertido");
  });

  it("keeps the amber row and its label in the compact view", async () => {
    renderAt("/p/duelo");
    const row = await rowOf(DISCARDED);
    await userEvent.click(screen.getByRole("button", { name: "Compacta" }));
    expect(document.querySelector('.list-box[data-density="compact"]')).not.toBeNull();
    expect(row).toHaveAttribute("data-commit-state", "discarded");
    expect(within(row).getByText("COMMIT DESHECHO")).toBeInTheDocument();
  });

  it("does not show the amber state on a PR", async () => {
    renderAt("/p/duelo");
    const row = await rowOf("feat: exponer ingesta de commits");
    expect(row).not.toHaveAttribute("data-commit-state");
  });
});

describe("undone commits in the detail", () => {
  it("warns that a reverted commit was reverted and links to the revert", async () => {
    renderAt("/p/duelo/changes/c4");
    const banner = await screen.findByRole("complementary", { name: "Estado del commit" });
    expect(banner).toHaveTextContent("COMMIT REVERTIDO");
    const link = within(banner).getByRole("link", { name: "d93f0b4" });
    expect(link).toHaveAttribute("href", "/p/duelo/changes/c5");
  });

  it("warns that a discarded commit is no longer on the branch", async () => {
    renderAt("/p/duelo/changes/c3");
    const banner = await screen.findByRole("complementary", { name: "Estado del commit" });
    expect(banner).toHaveTextContent("COMMIT DESHECHO");
    expect(banner).toHaveTextContent("Ya no está en la rama");
  });

  it("shows no warning for a normal commit", async () => {
    renderAt("/p/duelo/changes/c1");
    await screen.findByRole("heading", { name: /comparar el token/ });
    expect(screen.queryByRole("complementary", { name: "Estado del commit" })).toBeNull();
  });

  it("follows the link from a reverted commit to its revert", async () => {
    renderAt("/p/duelo/changes/c4");
    const banner = await screen.findByRole("complementary", { name: "Estado del commit" });
    await userEvent.click(within(banner).getByRole("link", { name: "d93f0b4" }));
    expect(await screen.findByRole("heading", { name: REVERT })).toBeInTheDocument();
    expect(screen.queryByRole("complementary", { name: "Estado del commit" })).toBeNull();
  });
});

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import type { Change } from "../data/mock";
import { DataSourceProvider } from "../data/source";
import type { DataSource } from "../lib/api";
import { NowProvider } from "../lib/now";
import { resetThemeForTests } from "../lib/theme";
import { makeChange, makeFinding, makeReview, makeSource } from "../test/fixtures";

const NOW = new Date("2026-10-09T12:00:00Z");

function renderWith(source: Partial<DataSource>, path: string) {
  const full = makeSource({
    health: async () => ({
      status: "ok",
      dependencies: [],
      agentNames: ["agent_1", "agent_2"],
    }),
    ...source,
  });
  return render(
    <DataSourceProvider source={full}>
      <NowProvider now={NOW}>
        <MemoryRouter initialEntries={[path]}>
          <App />
        </MemoryRouter>
      </NowProvider>
    </DataSourceProvider>,
  );
}

const light = (agent: string, status: "completed" | "failed" | "running") =>
  makeReview({ agent, status, partial: true });

const changes = (items: Change[]): Partial<DataSource> => ({
  changes: async () => ({ items, nextCursor: null }),
});

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  resetThemeForTests();
});

afterEach(() => vi.restoreAllMocks());

describe("app frame", () => {
  it("has a top bar with the brand and the theme switch, and a Slack-like sidebar", async () => {
    renderWith({}, "/p/demo");
    await screen.findByRole("heading", { name: "#demo" });
    expect(screen.getByRole("link", { name: "Duelo" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("group", { name: "Tema (cabecera)" })).toBeInTheDocument();
    const nav = within(screen.getByRole("navigation", { name: "Principal" }));
    expect(nav.getByRole("button", { name: /Proyectos/ })).toHaveAttribute("aria-expanded", "true");
    expect(nav.getByRole("link", { name: /demo/ })).toBeVisible();
  });

  it("collapses and expands the project channels", async () => {
    renderWith({}, "/p/demo");
    await screen.findByRole("heading", { name: "#demo" });
    const nav = within(screen.getByRole("navigation", { name: "Principal" }));
    const toggle = nav.getByRole("button", { name: /Proyectos/ });
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(nav.queryByRole("link", { name: /demo/ })).toBeNull();
    await userEvent.click(toggle);
    expect(nav.getByRole("link", { name: /demo/ })).toBeInTheDocument();
  });

  it("the channels list is an actual section: General links stay reachable while it is collapsed", async () => {
    renderWith({}, "/p/demo");
    await screen.findByRole("heading", { name: "#demo" });
    const nav = within(screen.getByRole("navigation", { name: "Principal" }));
    await userEvent.click(nav.getByRole("button", { name: /Proyectos/ }));
    expect(nav.getByRole("link", { name: "Estadísticas" })).toBeInTheDocument();
    expect(nav.getByRole("link", { name: "Ajustes" })).toBeInTheDocument();
  });
});

describe("channel rows (GitHub-style list)", () => {
  const rows = [
    makeChange({
      title: "fix: login",
      author: "ana",
      sha: "abc1234def",
      reviewStatus: "completed",
      reviews: [light("agent_1", "completed"), light("agent_2", "completed")],
    }),
    makeChange({
      title: "feat: pagos",
      author: "bob",
      sha: "fff0000aaa",
      reviewStatus: "partial_failed",
      reviews: [light("agent_1", "completed"), light("agent_2", "failed")],
    }),
    makeChange({ title: "chore: deps", author: "eva", reviewStatus: "pending", reviews: [] }),
  ];

  it("shows a state icon with a text alternative on every row", async () => {
    renderWith(changes(rows), "/p/demo");
    await screen.findByText("fix: login");
    expect(screen.getByRole("img", { name: "Completada" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Fallo parcial" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Pendiente" })).toBeInTheDocument();
  });

  it("writes the short SHA with a hash and the author, like a PR list", async () => {
    renderWith(changes(rows), "/p/demo");
    const row = (await screen.findByText("fix: login")).closest("li") as HTMLElement;
    expect(row).toHaveTextContent("#abc1234 · por ana");
  });

  it("shows one check per agent with its state as text", async () => {
    renderWith(changes(rows), "/p/demo");
    await screen.findByText("feat: pagos");
    const row = within((await screen.findByText("feat: pagos")).closest("li") as HTMLElement);
    const checks = row.getByRole("list", { name: "Checks de los agentes" });
    expect(within(checks).getByRole("img", { name: "Agent_1: completada" })).toBeInTheDocument();
    expect(within(checks).getByRole("img", { name: "Agent_2: fallida" })).toBeInTheDocument();
  });

  it("has no checks for a change nobody has reviewed yet", async () => {
    renderWith(changes(rows), "/p/demo");
    const row = within((await screen.findByText("chore: deps")).closest("li") as HTMLElement);
    expect(row.queryByRole("list", { name: "Checks de los agentes" })).toBeNull();
  });

  it("counts what is loaded by state in the list header", async () => {
    renderWith(changes(rows), "/p/demo");
    await screen.findByText("fix: login");
    expect(screen.getByText(/3 cambios · 1 en curso · 1 con fallos · 1 completados/)).toBeVisible();
  });

  it("flags that there may be more than what is counted when another page exists", async () => {
    renderWith({ changes: async () => ({ items: rows, nextCursor: "next" }) }, "/p/demo");
    await screen.findByText("fix: login");
    expect(screen.getByText(/3\+ cambios/)).toBeVisible();
  });

  it("styles the state filter as tabs and keeps them pressable", async () => {
    renderWith(changes(rows), "/p/demo");
    await screen.findByText("fix: login");
    const tabs = screen.getByRole("group", { name: "Estado de la review" });
    expect(within(tabs).getByRole("button", { name: "Todos" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});

describe("«/» focuses the search", () => {
  it("focuses the search box without typing a slash into it", async () => {
    renderWith({}, "/p/demo");
    const search = await screen.findByRole("searchbox", { name: "Buscar cambios" });
    expect(search).not.toHaveFocus();
    await userEvent.keyboard("/");
    expect(search).toHaveFocus();
    expect(search).toHaveValue("");
  });

  it("does not steal the key while the user is typing somewhere else", async () => {
    renderWith({}, "/p/demo");
    const search = await screen.findByRole("searchbox", { name: "Buscar cambios" });
    await userEvent.type(search, "a/b");
    expect(search).toHaveValue("a/b");
  });

  it("ignores it when a modal is open", async () => {
    renderWith({}, "/p/demo");
    const search = await screen.findByRole("searchbox", { name: "Buscar cambios" });
    const dialog = document.createElement("dialog");
    dialog.setAttribute("open", "");
    document.body.append(dialog);
    await userEvent.keyboard("/");
    expect(search).not.toHaveFocus();
    dialog.remove();
  });
});

describe("change detail as a conversation", () => {
  const change = makeChange({
    id: "c1",
    title: "feat: paginar",
    run: 1,
    reviewStatus: "completed",
    diff: [
      "diff --git a/a.py b/a.py",
      "--- a/a.py",
      "+++ b/a.py",
      "@@ -1,1 +1,2 @@",
      " keep",
      "+new",
    ].join("\n"),
    reviews: [
      makeReview({
        id: "r2",
        agent: "agent_2",
        run: 1,
        summary: "Segunda opinión",
        findings: [makeFinding({ severity: "nit", file: "a.py", line: 2, message: "Renombra x" })],
      }),
      makeReview({
        id: "r1",
        agent: "agent_1",
        run: 1,
        summary: "Primera opinión",
        findings: [
          makeFinding({ severity: "bug", file: "a.py", line: 1, message: "Falta un caso" }),
        ],
      }),
    ],
  });

  it("shows each agent's review as a message from an app, in a stable order", async () => {
    renderWith({ change: async () => change }, "/p/demo/changes/c1");
    const thread = (
      await screen.findByRole("heading", { name: "Revisión de los agentes" })
    ).closest("section") as HTMLElement;
    const messages = within(thread).getAllByRole("article");
    expect(messages).toHaveLength(2);
    expect(messages[0]).toHaveTextContent("Agent_1");
    expect(messages[1]).toHaveTextContent("Agent_2");
    for (const message of messages) expect(within(message).getByText("APP")).toBeInTheDocument();
  });

  it("lists each finding once: in the grouped panel, not repeated inside the messages", async () => {
    renderWith({ change: async () => change }, "/p/demo/changes/c1");
    await screen.findByRole("heading", { name: "Hallazgos" });
    expect(screen.getAllByText(/Falta un caso/)).toHaveLength(1);
    expect(screen.getAllByText(/Renombra x/)).toHaveLength(1);
  });

  it("keeps the findings inside the messages of the channel thread, where there is no panel", async () => {
    const full = makeChange({
      id: "c2",
      title: "fix: hilo",
      reviewStatus: "completed",
      reviews: [light("agent_1", "completed")],
    });
    renderWith(
      {
        ...changes([full]),
        change: async () => ({
          ...full,
          reviews: [
            makeReview({
              agent: "agent_1",
              summary: "Todo bien",
              findings: [makeFinding({ message: "Detalle importante" })],
            }),
          ],
        }),
      },
      "/p/demo",
    );
    await userEvent.click(await screen.findByRole("button", { name: "Ver respuestas" }));
    expect(await screen.findByText("Detalle importante")).toBeInTheDocument();
  });

  it("colors a finding's bar by severity: bug is red, risk amber, the rest neutral", async () => {
    const review = (severity: string) =>
      makeReview({
        agent: `a_${severity}`,
        run: 1,
        findings: [makeFinding({ severity, message: `m-${severity}`, file: `${severity}.py` })],
      });
    renderWith(
      {
        change: async () => ({
          ...change,
          reviews: [review("bug"), review("risk"), review("nit")],
        }),
      },
      "/p/demo/changes/c1",
    );
    await screen.findByRole("heading", { name: "Hallazgos" });
    const tone = (severity: string) =>
      screen
        .getByText(new RegExp(`m-${severity}`))
        .closest("li")
        ?.getAttribute("data-tone");
    expect(tone("bug")).toBe("danger");
    expect(tone("risk")).toBe("warning");
    expect(tone("nit")).toBe("neutral");
  });

  it("marks the file and hunk header rows of the diff so they can look like GitHub's", async () => {
    const { container } = renderWith({ change: async () => change }, "/p/demo/changes/c1");
    await screen.findByRole("table", { name: "Diff" });
    expect(container.querySelectorAll("tr.diff-row.header.file")).toHaveLength(1);
    expect(container.querySelectorAll("tr.diff-row.header.hunk")).toHaveLength(1);
  });

  it("shows the five-square bar beside each file as decoration only", async () => {
    renderWith({ change: async () => change }, "/p/demo/changes/c1");
    const nav = await screen.findByRole("navigation", { name: "Archivos del diff" });
    const squares = nav.querySelector(".squares");
    expect(squares).toHaveAttribute("aria-hidden", "true");
    expect(squares?.children).toHaveLength(5);
    expect(nav).toHaveTextContent("+1 −0");
  });

  it("shows the status as a pill with the state icon and its text", async () => {
    renderWith({ change: async () => change }, "/p/demo/changes/c1");
    await screen.findByRole("heading", { name: "feat: paginar" });
    const pill = document.querySelector(".status-pill") as HTMLElement;
    expect(pill).toHaveAttribute("data-tone", "success");
    expect(within(pill).getByRole("img", { name: "Completada" })).toBeInTheDocument();
  });
});

describe("statistics cards", () => {
  it("sums the agents and weights the averages by how many reviews each has", async () => {
    renderWith(
      {
        agentStats: async () => [
          { agent: "agent_1", total: 3, completed: 3, failed: 0, avgDurationMs: 1000, avgScore: 9 },
          { agent: "agent_2", total: 1, completed: 0, failed: 1, avgDurationMs: 5000, avgScore: 5 },
        ],
      },
      "/stats",
    );
    await waitFor(() => expect(document.querySelector(".stat-cards")).not.toBeNull());
    const region = document.querySelector(".stat-cards") as HTMLElement;
    expect(region).toHaveAttribute("aria-label", "Resumen global");
    const card = (label: string) =>
      within(region).getByText(label).closest(".stat-card") as HTMLElement;
    expect(card("Reviews totales")).toHaveTextContent("4");
    expect(card("Completadas")).toHaveTextContent("3");
    expect(card("Con fallo")).toHaveTextContent("1");
    // (1000*3 + 5000*1) / 4 = 2000 ms; (9*3 + 5*1) / 4 = 8
    expect(card("Duración media")).toHaveTextContent("2 s");
    expect(card("Nota media")).toHaveTextContent("8");
  });

  it("shows a dash instead of an average nobody reported", async () => {
    renderWith(
      {
        agentStats: async () => [
          {
            agent: "agent_1",
            total: 2,
            completed: 0,
            failed: 2,
            avgDurationMs: null,
            avgScore: null,
          },
        ],
      },
      "/stats",
    );
    await waitFor(() => expect(document.querySelector(".stat-cards")).not.toBeNull());
    const region = document.querySelector(".stat-cards") as HTMLElement;
    expect(within(region).getByText("Duración media").closest(".stat-card")).toHaveTextContent("—");
    expect(within(region).getByText("Nota media").closest(".stat-card")).toHaveTextContent("—");
  });
});

describe("settings: appearance", () => {
  it("has an Appearance box where the theme can be changed and is remembered", async () => {
    renderWith({}, "/settings");
    const box = within(
      (await screen.findByRole("heading", { name: "Apariencia" })).closest(
        "section",
      ) as HTMLElement,
    );
    await userEvent.click(box.getByRole("button", { name: "Oscuro" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(localStorage.getItem("duelo-theme")).toBe("dark");
    await userEvent.click(box.getByRole("button", { name: "Claro" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
  });

  it("the header switch and the Settings one stay in step", async () => {
    renderWith({}, "/settings");
    await screen.findByRole("heading", { name: "Apariencia" });
    await userEvent.click(screen.getByRole("button", { name: "Tema claro" }));
    expect(screen.getByRole("button", { name: "Claro" })).toHaveAttribute("aria-pressed", "true");
  });
});

describe("empty and missing states", () => {
  it("shows a not-found page with a heading and a way home", async () => {
    renderWith({}, "/nada/por/aqui");
    expect(await screen.findByRole("heading", { name: "No encontrado" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Volver al inicio" })).toHaveAttribute("href", "/");
  });

  it("explains an empty installation and offers the primary action", async () => {
    renderWith({ projects: async () => [] }, "/");
    expect(await screen.findByText("Aún no hay proyectos vigilados.")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Añadir proyecto" }).length).toBeGreaterThan(0);
  });

  it("draws loading placeholders, hidden from assistive technology, while the channel loads", async () => {
    let resolve: (v: { items: Change[]; nextCursor: null }) => void = () => {};
    renderWith(
      {
        changes: () =>
          new Promise((r) => {
            resolve = r;
          }),
      },
      "/p/demo",
    );
    const placeholder = await waitFor(() => {
      const el = document.querySelector(".skeleton");
      expect(el).not.toBeNull();
      return el as HTMLElement;
    });
    expect(placeholder).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByText("Cargando cambios…")).toBeInTheDocument();
    resolve({ items: [], nextCursor: null });
    await waitFor(() => expect(document.querySelector(".skeleton")).toBeNull());
  });
});

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { agentStats } from "../data/mock";
import { DataSourceProvider } from "../data/source";
import type { DataSource } from "../lib/api";
import { NowProvider } from "../lib/now";
import { makeChange, makeSource } from "../test/fixtures";

const NOW = new Date("2026-10-09T12:00:00Z");

function renderWith(source: Partial<DataSource>, path: string) {
  const full = makeSource(source);
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

afterEach(() => vi.restoreAllMocks());

describe("diff file navigator", () => {
  const diff = [
    "diff --git a/a.py b/a.py",
    "index 1..2 100644",
    "--- a/a.py",
    "+++ b/a.py",
    "@@ -1,2 +1,3 @@",
    " keep",
    "-old",
    "+new",
    "+extra",
    "diff --git a/b.py b/b.py",
    "--- a/b.py",
    "+++ b/b.py",
    "@@ -1,1 +1,2 @@",
    " keep",
    "+only",
  ].join("\n");

  it("lists each file with its counts and links to its section", async () => {
    renderWith({ change: async () => makeChange({ id: "c1", diff }) }, "/p/demo/changes/c1");
    const nav = await screen.findByRole("navigation", { name: "Archivos del diff" });
    expect(within(nav).getByRole("heading")).toHaveTextContent("2 archivos");
    const [first, second] = within(nav).getAllByRole("listitem");
    expect(first).toHaveTextContent("a.py +2 −1");
    expect(second).toHaveTextContent("b.py +1 −0");
    const href = within(second).getByRole("link", { name: "b.py" }).getAttribute("href");
    const target = document.getElementById(String(href).slice(1));
    expect(target).not.toBeNull();
    expect(target).toHaveTextContent("b.py");
  });

  it("does not render the navigator when the diff has no file names", async () => {
    renderWith(
      { change: async () => makeChange({ id: "c1", diff: "@@ -1,1 +1,2 @@\n ctx\n+n" }) },
      "/p/demo/changes/c1",
    );
    await screen.findByRole("table", { name: "Diff" });
    expect(screen.queryByRole("navigation", { name: "Archivos del diff" })).toBeNull();
  });
});

describe("sortable stats", () => {
  function bodyAgents() {
    return screen
      .getAllByRole("row")
      .slice(1)
      .map((row) => within(row).getByRole("rowheader").textContent);
  }

  it("sorts by a column, flips the direction and reports it with aria-sort", async () => {
    renderWith({ agentStats: async () => agentStats }, "/stats");
    const header = await screen.findByRole("columnheader", { name: "Fallos" });
    expect(header).not.toHaveAttribute("aria-sort");
    expect(bodyAgents()).toEqual(["Claude", "Codex"]);

    await userEvent.click(within(header).getByRole("button", { name: "Fallos" }));
    expect(header).toHaveAttribute("aria-sort", "ascending");
    expect(bodyAgents()).toEqual(["Claude", "Codex"]);

    await userEvent.click(within(header).getByRole("button", { name: "Fallos" }));
    expect(header).toHaveAttribute("aria-sort", "descending");
    expect(bodyAgents()).toEqual(["Codex", "Claude"]);
  });

  it("moves aria-sort to the newly chosen column", async () => {
    renderWith({ agentStats: async () => agentStats }, "/stats");
    const failures = await screen.findByRole("columnheader", { name: "Fallos" });
    const duration = screen.getByRole("columnheader", { name: "Duración media" });
    await userEvent.click(within(failures).getByRole("button"));
    await userEvent.click(within(duration).getByRole("button"));
    expect(failures).not.toHaveAttribute("aria-sort");
    expect(duration).toHaveAttribute("aria-sort", "ascending");
    expect(bodyAgents()).toEqual(["Codex", "Claude"]);
  });
});

describe("change age", () => {
  it("shows the relative age with the absolute date in <time>", async () => {
    const createdAt = "2026-10-09T11:48:00Z";
    renderWith(
      { changes: async () => ({ items: [makeChange({ createdAt })], nextCursor: null }) },
      "/p/demo",
    );
    const time = await screen.findByText("hace 12 min");
    expect(time.tagName).toBe("TIME");
    expect(time).toHaveAttribute("datetime", createdAt);
    expect(time).toHaveAttribute("title");
  });

  it("omits the age when the change has no date", async () => {
    renderWith(
      { changes: async () => ({ items: [makeChange({ title: "x" })], nextCursor: null }) },
      "/p/demo",
    );
    await screen.findByText("x");
    expect(document.querySelector("time")).toBeNull();
  });
});

describe("compact channel", () => {
  const items = [
    makeChange({ title: "alpha", author: "ana" }),
    makeChange({ title: "beta", author: "bob" }),
  ];

  it("toggles density and keeps the search and the thread controls", async () => {
    const changes: DataSource["changes"] = async (_slug, query) => ({
      items: items.filter((c) => !query?.q || c.author === query.q),
      nextCursor: null,
    });
    renderWith({ changes }, "/p/demo");
    await screen.findByText("alpha");
    expect(document.querySelectorAll(".change-row")).toHaveLength(0);

    await userEvent.type(screen.getByRole("searchbox"), "ana");
    await userEvent.click(screen.getByRole("button", { name: "Compacta" }));
    await waitFor(() => expect(screen.queryByText("beta")).toBeNull());

    expect(screen.getByRole("button", { name: "Compacta" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Tarjetas" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(document.querySelectorAll(".change-row")).toHaveLength(1);
    expect(screen.getByRole("searchbox")).toHaveValue("ana");
    expect(screen.getByRole("button", { name: "Ver respuestas" })).toBeInTheDocument();
  });
});

describe("actionable empty state", () => {
  it("shows the ingest command with the slug and a token placeholder", async () => {
    renderWith({}, "/p/demo");
    expect(await screen.findByText("Aún no hay cambios en este canal.")).toBeInTheDocument();
    const command = document.querySelector(".command code")?.textContent ?? "";
    expect(command).toContain('"project":"demo"');
    expect(command).toContain("$INGEST_TOKEN");
    expect(screen.getByRole("button", { name: "Copiar comando" })).toBeInTheDocument();
  });

  it("does not show it when a filter simply matches nothing", async () => {
    const changes: DataSource["changes"] = async (_slug, query) => ({
      items: query?.q ? [] : [makeChange({ title: "x" })],
      nextCursor: null,
    });
    renderWith({ changes }, "/p/demo");
    await screen.findByText("x");
    await userEvent.type(screen.getByRole("searchbox"), "zzz");
    expect(await screen.findByText("Ningún cambio coincide con la búsqueda.")).toBeInTheDocument();
    expect(screen.queryByText("Aún no hay cambios en este canal.")).toBeNull();
  });
});

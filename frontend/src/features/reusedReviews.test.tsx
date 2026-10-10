import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import App from "../App";
import { DataSourceProvider } from "../data/source";
import type { DataSource } from "../lib/api";
import { makeChange, makeReview, makeSource } from "../test/fixtures";

function renderWith(source: Partial<DataSource>, path: string) {
  return render(
    <DataSourceProvider source={makeSource(source)}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </DataSourceProvider>,
  );
}

const SHA = "3f2a9c1b7d4e5a6b8c9d0e1f2a3b4c5d6e7f8a9b";

// Origin: a PR identical to an already reviewed commit now reuses its reviews instead of asking
// the agents again; the page must say so and must not pretend the agents are still working.
const reusedPr = () =>
  makeChange({
    id: "c1",
    kind: "pr",
    title: "feat: algo",
    sha: SHA,
    run: 1,
    reviewStatus: "completed",
    reviews: [
      makeReview({ agent: "claude", run: 1, summary: "resumen de claude", reusedFrom: "commit-1" }),
      makeReview({ agent: "codex", run: 1, summary: "resumen de codex", reusedFrom: "commit-1" }),
    ],
  });

describe("a PR that reused the reviews of its commit", () => {
  it("marks every review with the commit it was copied from", async () => {
    renderWith({ change: async () => reusedPr() }, "/p/demo/changes/c1");

    expect(await screen.findByText("resumen de claude")).toBeInTheDocument();
    expect(screen.getAllByText("Reutilizada del commit 3f2a9c1")).toHaveLength(2);
  });

  it("does not show the agents as still reviewing", async () => {
    renderWith({ change: async () => reusedPr() }, "/p/demo/changes/c1");

    await screen.findByText("resumen de claude");
    expect(screen.queryByRole("list", { name: "Agentes pendientes" })).toBeNull();
    expect(screen.queryByText(/está revisando/)).toBeNull();
  });

  it("marks the reused reviews in the channel too", async () => {
    renderWith(
      {
        changes: async () => ({ items: [reusedPr()], nextCursor: null }),
        change: async () => reusedPr(),
      },
      "/p/demo",
    );

    const row = (await screen.findByText("feat: algo")).closest("li") as HTMLElement;
    expect(within(row).queryByText(/está revisando/)).toBeNull();
  });

  it("shows no pill on a normal PR", async () => {
    renderWith(
      {
        change: async () =>
          makeChange({
            id: "c1",
            kind: "pr",
            sha: SHA,
            reviewStatus: "completed",
            reviews: [makeReview({ agent: "claude", run: 1, summary: "propia" })],
          }),
      },
      "/p/demo/changes/c1",
    );

    expect(await screen.findByText("propia")).toBeInTheDocument();
    expect(screen.queryByText(/Reutilizada/)).toBeNull();
  });
});

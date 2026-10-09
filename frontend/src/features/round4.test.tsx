import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import type { AgentStat, Change, Health, ReviewAggregate } from "../data/mock";
import { DataSourceProvider } from "../data/source";
import { ApiError, type DataSource } from "../lib/api";
import { clearIngestToken, getIngestToken } from "../lib/ingestToken";
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

beforeEach(clearIngestToken);
afterEach(() => vi.restoreAllMocks());

describe("real stats", () => {
  const stat = (overrides: Partial<AgentStat>): AgentStat => ({
    agent: "claude",
    total: 4,
    completed: 3,
    failed: 1,
    avgDurationMs: 2500,
    avgScore: 7.5,
    ...overrides,
  });

  it("shows a loading state and then one row per agent with formatted values", async () => {
    renderWith(
      { agentStats: async () => [stat({}), stat({ agent: "codex", total: 9 })] },
      "/stats",
    );
    expect(screen.getByText("Cargando estadísticas…")).toBeInTheDocument();
    const row = await screen.findByRole("row", { name: /Claude/ });
    expect(row).toHaveTextContent("2,5 s");
    expect(row).toHaveTextContent("7,5");
    expect(screen.getByRole("row", { name: /Codex/ })).toHaveTextContent("9");
  });

  it("shows the empty state", async () => {
    renderWith({ agentStats: async () => [] }, "/stats");
    expect(await screen.findByText("Aún no hay reviews registradas.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("shows a recoverable error", async () => {
    const agentStats = vi
      .fn<DataSource["agentStats"]>()
      .mockRejectedValueOnce(new ApiError("El servidor respondió 503.", 503))
      .mockResolvedValue([stat({})]);
    renderWith({ agentStats }, "/stats");
    expect(await screen.findByRole("alert")).toHaveTextContent("503");
    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByRole("row", { name: /Claude/ })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows a dash for missing averages and sorts them last in both directions", async () => {
    renderWith(
      {
        agentStats: async () => [
          stat({ agent: "codex", avgScore: null, avgDurationMs: null }),
          stat({ agent: "claude", avgScore: 6 }),
        ],
      },
      "/stats",
    );
    const nobody = await screen.findByRole("row", { name: /Codex/ });
    expect(within(nobody).getAllByText("—")).toHaveLength(2);
    const agents = () =>
      screen
        .getAllByRole("row")
        .slice(1)
        .map((row) => within(row).getByRole("rowheader").textContent);
    const header = screen.getByRole("columnheader", { name: "Nota media" });
    await userEvent.click(within(header).getByRole("button"));
    expect(agents()).toEqual(["Claude", "Codex"]);
    await userEvent.click(within(header).getByRole("button"));
    expect(agents()).toEqual(["Claude", "Codex"]);
  });
});

describe("retry review", () => {
  const failed = (overrides: Partial<Change> = {}) =>
    makeChange({
      id: "d1",
      title: "detalle",
      reviewStatus: "failed",
      run: 1,
      reviews: [makeReview({ status: "failed" })],
      ...overrides,
    });
  const path = "/p/demo/changes/d1";
  const retryButton = () => screen.getByRole("button", { name: "Reintentar review" });
  const tokenField = () => screen.getByLabelText("Token de ingesta");

  it.each<ReviewAggregate>(["pending", "running", "completed"])(
    "is hidden when the change is %s",
    async (reviewStatus) => {
      renderWith({ change: async () => failed({ reviewStatus }) }, path);
      await screen.findByRole("heading", { name: "detalle" });
      expect(screen.queryByRole("button", { name: "Reintentar review" })).toBeNull();
      expect(screen.queryByLabelText("Token de ingesta")).toBeNull();
    },
  );

  it.each<ReviewAggregate>(["failed", "partial_failed"])("is offered when %s", async (status) => {
    renderWith({ change: async () => failed({ reviewStatus: status }) }, path);
    expect(await screen.findByRole("button", { name: "Reintentar review" })).toBeInTheDocument();
    expect(tokenField()).toHaveAttribute("type", "password");
  });

  it("shows the aggregate status and the run in the header", async () => {
    renderWith({ change: async () => failed({ reviewStatus: "partial_failed", run: 3 }) }, path);
    expect(await screen.findByText("Fallo parcial")).toBeInTheDocument();
    expect(screen.getByText("Run 3")).toBeInTheDocument();
  });

  it("asks for the token and does not call the API without one", async () => {
    const retry = vi.fn<DataSource["retry"]>();
    renderWith({ change: async () => failed(), retry }, path);
    await screen.findByRole("heading", { name: "detalle" });
    await userEvent.click(retryButton());
    expect(await screen.findByRole("alert")).toHaveTextContent("Introduce el token");
    expect(retry).not.toHaveBeenCalled();
  });

  it("sends the trimmed token, announces the new run and reloads the detail", async () => {
    let current = failed();
    const retry = vi.fn<DataSource["retry"]>(async () => {
      current = failed({ reviewStatus: "pending", run: 2, reviews: [] });
      return { changeId: "d1", run: 2 };
    });
    const change = vi.fn<DataSource["change"]>(async () => current);
    renderWith({ change, retry }, path);
    await screen.findByRole("heading", { name: "detalle" });
    await userEvent.type(tokenField(), " secreto ");
    await userEvent.click(retryButton());
    expect(await screen.findByText("Reintento en marcha (run 2).")).toBeInTheDocument();
    expect(retry).toHaveBeenCalledWith("d1", "secreto");
    expect(change).toHaveBeenCalledTimes(2);
    expect(screen.getByText("Pendiente")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reintentar review" })).toBeNull();
  });

  it("forgets the token and says it is not valid on 401", async () => {
    const retry = vi.fn<DataSource["retry"]>().mockRejectedValue(new ApiError("x", 401));
    renderWith({ change: async () => failed(), retry }, path);
    await screen.findByRole("heading", { name: "detalle" });
    await userEvent.type(tokenField(), "malo");
    await userEvent.click(retryButton());
    expect(await screen.findByRole("alert")).toHaveTextContent("Token de ingesta no válido.");
    expect(tokenField()).toHaveValue("");
    expect(getIngestToken()).toBe("");
  });

  it("says it can no longer be retried on 409 and reloads the detail", async () => {
    const retry = vi.fn<DataSource["retry"]>().mockRejectedValue(new ApiError("x", 409));
    const change = vi.fn<DataSource["change"]>(async () => failed());
    renderWith({ change, retry }, path);
    await screen.findByRole("heading", { name: "detalle" });
    await userEvent.type(tokenField(), "tok");
    await userEvent.click(retryButton());
    expect(await screen.findByText(/ya no se puede reintentar/)).toBeInTheDocument();
    await waitFor(() => expect(change).toHaveBeenCalledTimes(2));
  });

  it.each([
    [503, "El orquestador no está disponible"],
    [404, "Change no encontrado."],
    [null, "No se pudo conectar con el servidor."],
  ])("explains a %s failure and allows trying again", async (status, text) => {
    const retry = vi
      .fn<DataSource["retry"]>()
      .mockRejectedValueOnce(new ApiError("No se pudo conectar con el servidor.", status))
      .mockResolvedValue({ changeId: "d1", run: 2 });
    renderWith({ change: async () => failed(), retry }, path);
    await screen.findByRole("heading", { name: "detalle" });
    await userEvent.type(tokenField(), "tok");
    await userEvent.click(retryButton());
    expect(await screen.findByRole("alert")).toHaveTextContent(text);
    expect(tokenField()).toHaveValue("tok");
    await userEvent.click(retryButton());
    expect(await screen.findByText("Reintento en marcha (run 2).")).toBeInTheDocument();
    expect(retry).toHaveBeenCalledTimes(2);
  });

  it("allows a single request at a time", async () => {
    let release: (value: { changeId: string; run: number }) => void = () => {};
    const retry = vi.fn<DataSource["retry"]>(
      () =>
        new Promise((resolve) => {
          release = resolve;
        }),
    );
    renderWith({ change: async () => failed(), retry }, path);
    await screen.findByRole("heading", { name: "detalle" });
    await userEvent.type(tokenField(), "tok");
    await userEvent.click(retryButton());
    const busy = await screen.findByRole("button", { name: "Reintentando…" });
    expect(busy).toBeDisabled();
    await userEvent.click(busy);
    expect(retry).toHaveBeenCalledTimes(1);
    release({ changeId: "d1", run: 2 });
    expect(await screen.findByText("Reintento en marcha (run 2).")).toBeInTheDocument();
  });

  it("keeps the token in memory only", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    const retry = vi.fn<DataSource["retry"]>(async () => ({ changeId: "d1", run: 2 }));
    renderWith({ change: async () => failed(), retry }, path);
    await screen.findByRole("heading", { name: "detalle" });
    await userEvent.type(tokenField(), "secretisimo");
    await userEvent.click(retryButton());
    await screen.findByText("Reintento en marcha (run 2).");
    expect(setItem).not.toHaveBeenCalled();
    expect(`${JSON.stringify(localStorage)}${JSON.stringify(sessionStorage)}`).not.toContain(
      "secretisimo",
    );
    expect(document.body.textContent).not.toContain("secretisimo");
  });
});

describe("settings diagnostics", () => {
  const projectsSection = () => screen.getByRole("region", { name: "Proyectos vigilados" });
  const diagnosticsSection = () => screen.getByRole("region", { name: "Diagnóstico" });

  const health = (overrides: Partial<Health> = {}): Health => ({
    status: "ok",
    dependencies: [
      { name: "postgres", status: "ok", latencyMs: 4 },
      { name: "temporal", status: "ok", latencyMs: 12 },
    ],
    ...overrides,
  });

  it("lists the projects and each dependency with its latency", async () => {
    renderWith(
      {
        projects: async () => [
          { slug: "acme/widgets", name: "acme/widgets" },
          { slug: "demo", name: "demo" },
        ],
        health: async () => health(),
      },
      "/settings",
    );
    expect(await within(projectsSection()).findByText("acme/widgets")).toBeInTheDocument();
    expect(within(projectsSection()).getByText("demo")).toBeInTheDocument();
    expect(await screen.findByText("Correcto")).toBeInTheDocument();
    expect(screen.getByText("Postgres").closest(".setting")).toHaveTextContent("4 ms");
    expect(screen.getByText("Temporal").closest(".setting")).toHaveTextContent("12 ms");
  });

  it("shows a degraded server and the translated reason, never free text", async () => {
    renderWith(
      {
        health: async () =>
          health({
            status: "degraded",
            dependencies: [
              { name: "postgres", status: "ok", latencyMs: 4 },
              { name: "temporal", status: "unavailable", latencyMs: 2000, reason: "timeout" },
            ],
          }),
      },
      "/settings",
    );
    expect(await screen.findByText("Degradado")).toBeInTheDocument();
    const temporal = screen.getByText("Temporal").closest(".setting");
    expect(temporal).toHaveTextContent("No disponible");
    expect(temporal).toHaveTextContent("Tiempo agotado");
    expect(temporal).toHaveTextContent("2000 ms");
  });

  it("keeps the projects visible when only the diagnostics fail, and refreshes them", async () => {
    const healthCall = vi
      .fn<DataSource["health"]>()
      .mockRejectedValueOnce(new ApiError("El servidor respondió 500.", 500))
      .mockResolvedValue(health());
    renderWith({ health: healthCall }, "/settings");
    expect(await within(diagnosticsSection()).findByRole("alert")).toHaveTextContent("500");
    expect(await within(projectsSection()).findByText("demo")).toBeInTheDocument();
    await userEvent.click(within(diagnosticsSection()).getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Correcto")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Actualizar" }));
    await waitFor(() => expect(healthCall).toHaveBeenCalledTimes(3));
  });

  it("keeps the diagnostics visible when only the projects fail", async () => {
    renderWith(
      {
        projects: async () => {
          throw new ApiError("El servidor respondió 500.", 500);
        },
        health: async () => health(),
      },
      "/settings",
    );
    expect(await screen.findByText("Correcto")).toBeInTheDocument();
    expect(within(projectsSection()).getByRole("alert")).toHaveTextContent("500");
    expect(within(diagnosticsSection()).queryByRole("alert")).toBeNull();
  });
});

describe("review metadata", () => {
  const detail = (reviews: ReturnType<typeof makeReview>[]) =>
    makeChange({ id: "d1", title: "detalle", reviews });

  it("shows run, duration and score on a completed review", async () => {
    renderWith(
      {
        change: async () =>
          detail([makeReview({ summary: "ok", run: 2, durationMs: 42_000, score: 8 })]),
      },
      "/p/demo/changes/d1",
    );
    const meta = await screen.findByRole("list", { name: "Datos de la review" });
    expect(within(meta).getByText("Run 2")).toBeInTheDocument();
    expect(within(meta).getByText("42 s")).toBeInTheDocument();
    expect(within(meta).getByText("Nota 8")).toBeInTheDocument();
  });

  it("omits the metadata list when the source has none", async () => {
    renderWith(
      { change: async () => detail([makeReview({ summary: "ok" })]) },
      "/p/demo/changes/d1",
    );
    await screen.findByText("ok");
    expect(screen.queryByRole("list", { name: "Datos de la review" })).toBeNull();
  });

  it("shows a sanitized failure reason as plain text", async () => {
    renderWith(
      {
        change: async () =>
          detail([
            makeReview({
              status: "failed",
              error: "boom token=abc123\u0000 <img src=x onerror=alert(1)>",
            }),
          ]),
      },
      "/p/demo/changes/d1",
    );
    const reason = await screen.findByText(/^Motivo:/);
    expect(reason).toHaveTextContent("boom token=[oculto]");
    expect(reason).not.toHaveTextContent("abc123");
    expect(reason.querySelector("img")).toBeNull();
  });

  it("does not show a reason for a review that did not fail", async () => {
    renderWith(
      { change: async () => detail([makeReview({ summary: "ok", error: "ignorado" })]) },
      "/p/demo/changes/d1",
    );
    await screen.findByText("ok");
    expect(screen.queryByText(/Motivo:/)).toBeNull();
  });
});

describe("aggregate status in the channel", () => {
  it("shows the aggregate status badge when the listing has no reviews", async () => {
    renderWith(
      {
        changes: async () => ({
          items: [makeChange({ title: "x", reviews: undefined, reviewStatus: "partial_failed" })],
          nextCursor: null,
        }),
      },
      "/p/demo",
    );
    const summary = await screen.findByRole("list", { name: "Resumen de reviews" });
    expect(within(summary).getByText("Fallo parcial")).toBeInTheDocument();
  });

  it("prefers the per-review counts when the reviews are present", async () => {
    renderWith(
      {
        changes: async () => ({
          items: [
            makeChange({
              title: "x",
              reviewStatus: "completed",
              reviews: [makeReview(), makeReview()],
            }),
          ],
          nextCursor: null,
        }),
      },
      "/p/demo",
    );
    const summary = await screen.findByRole("list", { name: "Resumen de reviews" });
    expect(within(summary).getByText("2 completadas")).toBeInTheDocument();
    expect(within(summary).queryByText("Completada")).toBeNull();
  });
});

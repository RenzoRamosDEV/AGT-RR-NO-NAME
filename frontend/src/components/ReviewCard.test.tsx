import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { makeFinding, makeReview } from "../test/fixtures";
import { resetCollapsibleMemory } from "./Collapsible";
import { ReviewCard } from "./ReviewCard";
import { agentLogo } from "./ui/AgentAvatar";

afterEach(resetCollapsibleMemory);

describe("ReviewCard", () => {
  it("shows the agent's logo as the avatar of its message", () => {
    const { container } = render(<ReviewCard review={makeReview({ agent: "codex" })} />);
    expect(container.querySelector(".avatar img")).toHaveAttribute("src", agentLogo("codex"));
  });

  describe("a review reused from the commit", () => {
    it("says which commit it was copied from, with the short SHA", () => {
      render(
        <ReviewCard
          review={makeReview({ reusedFrom: "origin-change-id" })}
          sha="3f2a9c1b7d4e5a6b8c9d0e1f2a3b4c5d6e7f8a9b"
        />,
      );
      const pill = screen.getByText("Reutilizada del commit 3f2a9c1");
      expect(pill).toHaveAttribute("title", expect.stringContaining("commit 3f2a9c1"));
      expect(pill).toHaveAttribute("title", expect.stringContaining("no se volvió a pedir"));
    });

    it("still says it is reused when the SHA is not known", () => {
      render(<ReviewCard review={makeReview({ reusedFrom: "origin-change-id" })} />);
      expect(screen.getByText("Reutilizada del commit")).toBeInTheDocument();
    });

    it("shows no pill on a review the agent made itself", () => {
      const { rerender } = render(
        <ReviewCard review={makeReview({ reusedFrom: null })} sha="3f2a9c1b7d" />,
      );
      expect(screen.queryByText(/Reutilizada/)).toBeNull();
      rerender(<ReviewCard review={makeReview()} sha="3f2a9c1b7d" />);
      expect(screen.queryByText(/Reutilizada/)).toBeNull();
    });
  });

  it("puts the author, the APP tag, the status and the data on the header line", () => {
    render(
      <ReviewCard
        review={makeReview({ agent: "claude", run: 2, durationMs: 11000, score: 9, summary: "ok" })}
      />,
    );
    expect(screen.getByText("Claude")).toBeInTheDocument();
    expect(screen.getByText("APP")).toBeInTheDocument();
    expect(screen.getByText("Completada")).toBeInTheDocument();
    const meta = screen.getByRole("list", { name: "Datos de la review" });
    expect(
      within(meta)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["Run 2", "11 s", "Nota 9"]);
  });

  // Regresión: el resumen salía como un párrafo pegado con los backticks literales.
  it("renders the summary as formatted paragraphs under a «Resumen» label", () => {
    const { container } = render(
      <ReviewCard
        review={makeReview({
          summary: "Cambio solo la documentación (`README.md`).\n\nNo verifiqué `redact_secrets`.",
        })}
      />,
    );
    const summary = screen.getByRole("region", { name: "Resumen" });
    expect(within(summary).getByRole("heading", { name: "Resumen" })).toBeInTheDocument();
    expect(summary.querySelectorAll("p")).toHaveLength(2);
    expect(summary.querySelectorAll("code")).toHaveLength(2);
    expect(container).not.toHaveTextContent("`");
  });

  it("folds a long summary and keeps it open after a refresh", async () => {
    const user = userEvent.setup();
    const long = makeReview({ id: "long-summary", summary: "frase larga. ".repeat(60) });
    const { rerender } = render(<ReviewCard review={long} />);
    await user.click(screen.getByRole("button", { name: "Ver más" }));
    // The polling hands the card a new object for the same review.
    rerender(<ReviewCard review={{ ...long, durationMs: 5 }} />);
    expect(screen.getByRole("button", { name: "Ver menos" })).toBeInTheDocument();
  });

  it("lists the findings as cards under a counted «Hallazgos» label, most serious first", () => {
    render(
      <ReviewCard
        review={makeReview({
          id: "r-order",
          summary: "s",
          findings: [
            makeFinding({ severity: "nit", message: "detalle" }),
            makeFinding({ severity: "bug", message: "grave" }),
            makeFinding({ severity: "risk", message: "medio" }),
          ],
        })}
      />,
    );
    const panel = screen.getByRole("region", { name: "Hallazgos" });
    expect(within(panel).getByText("3")).toBeInTheDocument();
    const items = within(panel).getAllByRole("listitem");
    expect(items.map((li) => /grave|medio|detalle/.exec(li.textContent ?? "")?.[0])).toEqual([
      "grave",
      "medio",
      "detalle",
    ]);
  });

  it("does not list the findings where a grouped panel already does", () => {
    render(
      <ReviewCard
        review={makeReview({ summary: "s", findings: [makeFinding({ message: "una" })] })}
        showFindings={false}
      />,
    );
    expect(screen.queryByText("una")).toBeNull();
    expect(screen.queryByRole("region", { name: "Hallazgos" })).toBeNull();
  });

  it("says «Sin hallazgos» when a completed review has none", () => {
    render(<ReviewCard review={makeReview({ summary: "todo bien", findings: [] })} />);
    expect(screen.getByText("Sin hallazgos")).toBeInTheDocument();
  });

  it("shows the sanitized reason of a failed review in an error box, with no summary", () => {
    render(
      <ReviewCard
        review={makeReview({
          status: "failed",
          summary: "no debería verse",
          error: "falló con token=abc123",
        })}
      />,
    );
    expect(screen.getByText("La review no pudo completarse.")).toBeInTheDocument();
    expect(screen.getByText(/Motivo:/)).not.toHaveTextContent("abc123");
    expect(screen.queryByText("no debería verse")).toBeNull();
    expect(screen.queryByRole("region", { name: "Resumen" })).toBeNull();
  });

  it("shows no summary or findings for a light review from the channel listing", () => {
    render(<ReviewCard review={makeReview({ partial: true, durationMs: 3000 })} />);
    expect(screen.queryByRole("region", { name: "Resumen" })).toBeNull();
    expect(screen.queryByText("Sin hallazgos")).toBeNull();
  });

  it("shows a running review as thinking", () => {
    render(<ReviewCard review={makeReview({ status: "running", agent: "codex" })} />);
    expect(screen.getByText("Codex está revisando…")).toBeInTheDocument();
  });
});

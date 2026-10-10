import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type { Change } from "../data/mock";
import { undoneNotice } from "../lib/commitState";
import { UndoneBanner, UndoneLabel, UndoneStatusIcon } from "./UndoneNotice";

const base: Change = {
  id: "c1",
  kind: "commit",
  title: "feat: algo",
  author: "ana",
  sha: "abc1234abc1234",
  ref: "main",
  url: "",
  diff: "",
};

const discarded: Change = { ...base, commitState: "discarded" };
const reverted: Change = {
  ...base,
  commitState: "reverted",
  revertedBy: { id: "c9", sha: "d93f0b4aaaaa" },
};

function renderBanner(change: Change) {
  return render(
    <MemoryRouter>
      <UndoneBanner change={change} slug="acme/widgets" />
    </MemoryRouter>,
  );
}

describe("UndoneStatusIcon", () => {
  it("is an image whose text alternative is the state in words, not only a colour", () => {
    const notice = undoneNotice(discarded);
    if (!notice) throw new Error("expected a notice");
    render(<UndoneStatusIcon notice={notice} />);
    const icon = screen.getByRole("img", { name: "COMMIT DESHECHO" });
    expect(icon).toHaveAttribute("data-tone", "warning");
  });
});

describe("UndoneLabel", () => {
  it("shows the headline in capitals and its subtitle", () => {
    const notice = undoneNotice(reverted);
    if (!notice) throw new Error("expected a notice");
    const { container } = render(<UndoneLabel notice={notice} />);
    expect(screen.getByText("COMMIT REVERTIDO")).toBeInTheDocument();
    expect(screen.getByText("Revertido por d93f0b4")).toBeInTheDocument();
    expect(container.querySelector(".undone-label")).toHaveAttribute("data-state", "reverted");
  });
});

describe("UndoneBanner", () => {
  it("warns that a discarded commit is no longer on the branch and keeps its reviews", () => {
    renderBanner(discarded);
    const banner = screen.getByRole("complementary", { name: "Estado del commit" });
    expect(banner).toHaveTextContent("COMMIT DESHECHO");
    expect(banner).toHaveTextContent("Ya no está en la rama.");
    expect(banner).toHaveTextContent("Sus reviews se conservan.");
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("links a reverted commit to the commit that reverts it", () => {
    renderBanner(reverted);
    expect(screen.getByText("COMMIT REVERTIDO")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "d93f0b4" });
    expect(link).toHaveAttribute("href", "/p/acme/widgets/changes/c9");
  });

  it("does not invent a link when the reverting commit is unknown", () => {
    renderBanner({ ...reverted, revertedBy: undefined });
    expect(screen.getByText(/Revertido por otro commit\./)).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull();
  });

  it.each([
    ["a normal commit", { ...base, commitState: "active" as const }],
    ["a commit without a state", base],
    ["a PR", { ...base, kind: "pr" as const, commitState: "discarded" as const }],
  ])("renders nothing for %s", (_name, change) => {
    const { container } = renderBanner(change);
    expect(container).toBeEmptyDOMElement();
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Beam } from "./Beam";

function setReducedMotion(reduced: boolean) {
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query: string) =>
      ({
        matches: reduced && query.includes("reduce"),
        media: query,
        addEventListener: () => {},
        removeEventListener: () => {},
      }) as unknown as MediaQueryList,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("Beam (border-beam)", () => {
  it("wraps what is in progress with the beam, and the content is there the whole time", async () => {
    const { container } = render(
      <Beam active>
        <p>fila en curso</p>
      </Beam>,
    );
    // While the chunk loads the content is shown as it is...
    expect(screen.getByText("fila en curso")).toBeInTheDocument();
    // ...and then it is wrapped by the beam.
    await waitFor(() => expect(container.querySelector(".beam")).not.toBeNull());
    expect(container.querySelector(".beam")).toContainElement(screen.getByText("fila en curso"));
  });

  it("leaves a finished row alone: no wrapper, no cost", () => {
    const { container } = render(
      <Beam active={false}>
        <p>fila terminada</p>
      </Beam>,
    );
    expect(screen.getByText("fila terminada")).toBeInTheDocument();
    expect(container.querySelector(".beam")).toBeNull();
  });

  it("never animates under prefers-reduced-motion, even for something in progress", async () => {
    setReducedMotion(true);
    const { container } = render(
      <Beam active>
        <p>fila en curso</p>
      </Beam>,
    );
    expect(screen.getByText("fila en curso")).toBeInTheDocument();
    // Give a lazy chunk the chance it would need to show up, then check that it never did.
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(container.querySelector(".beam")).toBeNull();
  });
});

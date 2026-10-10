import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MetalButton } from "./MetalButton";
import { resetWebGLForTests } from "./webgl";

// The real ring needs WebGL2, which jsdom lacks: this stand-in records that it wrapped the button.
vi.mock("./MetalRing", () => ({
  default: ({ theme, children }: { theme: string; children: React.ReactNode }) => (
    <div data-metal-ring data-theme={theme}>
      {children}
    </div>
  ),
}));

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

/** Makes `canvas.getContext("webgl2")` answer, as a browser with a GPU would. */
function withWebGL2() {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation((() => ({})) as never);
}

beforeEach(resetWebGLForTests);
afterEach(() => {
  vi.restoreAllMocks();
  resetWebGLForTests();
});

describe("MetalButton (metal-fx)", () => {
  it("is the plain neutral button where there is no WebGL2", () => {
    const { container } = render(<MetalButton variant="primary">Añadir proyecto</MetalButton>);
    const button = screen.getByRole("button", { name: "Añadir proyecto" });
    // The ring replaces the fill, so the white-on-green primary look must never be used.
    expect(button).toHaveClass("btn", "btn-metal");
    expect(button).not.toHaveClass("btn-primary");
    expect(container.querySelector("[data-metal-ring]")).toBeNull();
  });

  it("wraps the button in the metal ring when WebGL2 is there, keeping it a real button", async () => {
    withWebGL2();
    const onClick = vi.fn();
    const { container } = render(<MetalButton onClick={onClick}>Reintentar review</MetalButton>);
    await waitFor(() => expect(container.querySelector("[data-metal-ring]")).not.toBeNull());
    const button = screen.getByRole("button", { name: "Reintentar review" });
    expect(container.querySelector("[data-metal-ring]")).toContainElement(button);
    expect(container.querySelector("[data-metal-ring]")).toHaveAttribute("data-theme", "dark");
    button.click();
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("keeps its disabled state and extra classes", () => {
    render(
      <MetalButton disabled className="extra">
        Enviando
      </MetalButton>,
    );
    const button = screen.getByRole("button", { name: "Enviando" });
    expect(button).toBeDisabled();
    expect(button).toHaveClass("btn-metal", "extra");
  });

  it("drops the ring under prefers-reduced-motion even with WebGL2", async () => {
    withWebGL2();
    setReducedMotion(true);
    const { container } = render(<MetalButton>Añadir proyecto</MetalButton>);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(screen.getByRole("button", { name: "Añadir proyecto" })).toBeInTheDocument();
    expect(container.querySelector("[data-metal-ring]")).toBeNull();
  });
});

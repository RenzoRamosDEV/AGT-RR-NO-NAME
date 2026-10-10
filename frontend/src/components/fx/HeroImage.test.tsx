import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EmptyState } from "../EmptyState";
import { HeroImage } from "./HeroImage";
import { resetWebGLForTests } from "./webgl";

// The real effect needs WebGL (and `three`); this stand-in records what it was asked to draw.
vi.mock("./HeroImageFx", () => ({
  default: (props: { src: string; width: number; height: number }) => (
    <div data-hero-fx data-src={props.src} data-width={props.width} data-height={props.height} />
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

function withWebGL() {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation((() => ({})) as never);
}

beforeEach(resetWebGLForTests);
afterEach(() => {
  vi.restoreAllMocks();
  resetWebGLForTests();
});

describe("HeroImage (img-fx)", () => {
  it("is the plain picture where there is no WebGL, and decorative", () => {
    const { container } = render(<HeroImage src="/hero.png" />);
    const img = container.querySelector("img.hero-img");
    expect(img).toHaveAttribute("src", "/hero.png");
    // Decorative art: empty alt, so a screen reader reads the title and the text, not "image".
    expect(img).toHaveAttribute("alt", "");
    expect(container.querySelector("[data-hero-fx]")).toBeNull();
  });

  it("plays the loader-to-image effect with WebGL, showing the picture while the chunk loads", async () => {
    withWebGL();
    const { container } = render(<HeroImage src="/hero.png" />);
    expect(container.querySelector("img.hero-img")).toHaveAttribute("src", "/hero.png");
    await waitFor(() => expect(container.querySelector("[data-hero-fx]")).not.toBeNull());
    const fx = container.querySelector("[data-hero-fx]");
    expect(fx).toHaveAttribute("data-src", "/hero.png");
    expect(fx).toHaveAttribute("data-width", "240");
    expect(container.querySelector(".hero")).toHaveAttribute("data-fx", "img");
  });

  it("stays the plain picture under prefers-reduced-motion, even with WebGL", async () => {
    withWebGL();
    setReducedMotion(true);
    const { container } = render(<HeroImage src="/hero.png" />);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(container.querySelector("img.hero-img")).toBeInTheDocument();
    expect(container.querySelector("[data-hero-fx]")).toBeNull();
  });
});

describe("EmptyState hero", () => {
  it("uses the hero picture instead of the line illustration when it is given one", () => {
    const { container } = render(<EmptyState hero="/hero.png" title="Aún no hay nada." />);
    expect(screen.getByText("Aún no hay nada.")).toBeInTheDocument();
    expect(container.querySelector("img.hero-img")).toHaveAttribute("src", "/hero.png");
    expect(container.querySelector("svg.empty-art")).toBeNull();
  });

  it("keeps the line illustration when there is no hero", () => {
    const { container } = render(<EmptyState kind="missing" title="No encontrado" />);
    expect(container.querySelector("svg.empty-art")).toBeInTheDocument();
    expect(container.querySelector("img.hero-img")).toBeNull();
  });
});

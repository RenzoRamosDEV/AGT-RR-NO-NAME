import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { resetThemeForTests, setThemePreference } from "../lib/theme";
import { BrandLogo } from "./BrandLogo";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  resetThemeForTests();
});

afterEach(() => resetThemeForTests());

const logo = () => document.querySelector<HTMLImageElement>("img.brand-logo") as HTMLImageElement;

describe("BrandLogo", () => {
  it("shows the neon emblem on the dark theme and the 3D one on the light theme", () => {
    setThemePreference("dark");
    const { unmount } = render(<BrandLogo />);
    expect(logo()).toHaveAttribute("data-variant", "dark");
    expect(logo().getAttribute("src")).toContain("mark-dark");
    unmount();

    setThemePreference("light");
    render(<BrandLogo />);
    expect(logo()).toHaveAttribute("data-variant", "light");
    expect(logo().getAttribute("src")).toContain("mark-light");
  });

  it("swaps the picture in place when the theme changes, without remounting", () => {
    setThemePreference("dark");
    render(<BrandLogo />);
    const before = logo();
    expect(before.getAttribute("src")).toContain("mark-dark");

    act(() => setThemePreference("light"));

    expect(logo()).toBe(before);
    expect(logo().getAttribute("src")).toContain("mark-light");
    expect(logo().getAttribute("srcset")).toContain("mark-light");
    expect(logo().getAttribute("srcset")).not.toContain("mark-dark");
  });

  it("follows the system color scheme while the choice is System", () => {
    document.documentElement.setAttribute("data-theme", "light");
    window.matchMedia = ((query: string) => ({
      matches: query.includes("light"),
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    })) as unknown as typeof window.matchMedia;
    resetThemeForTests();

    render(<BrandLogo />);

    expect(logo()).toHaveAttribute("data-variant", "light");
  });

  it("reserves its size, so swapping themes cannot move the layout", () => {
    render(<BrandLogo size={28} />);
    expect(logo()).toHaveAttribute("width", "28");
    expect(logo()).toHaveAttribute("height", "28");
    expect(logo()).toHaveAttribute("decoding", "async");
  });

  it("asks for the 32 and 64 px files up to 32 px and for the 64 and 128 px files above", () => {
    const { rerender } = render(<BrandLogo size={28} />);
    expect(logo().getAttribute("srcset")).toMatch(/mark-\w+-32.*1x.*mark-\w+-64.*2x/);

    rerender(<BrandLogo size={56} />);
    expect(logo().getAttribute("srcset")).toMatch(/mark-\w+-64.*1x.*mark-\w+-128.*2x/);
  });

  it("is decorative by default, because the name is written next to it", () => {
    render(<BrandLogo />);
    expect(logo()).toHaveAttribute("alt", "");
    expect(screen.queryByRole("img", { name: "Duelo" })).toBeNull();
  });

  it("is announced as «Duelo» when it stands alone", () => {
    render(<BrandLogo decorative={false} />);
    expect(screen.getByRole("img", { name: "Duelo" })).toBe(logo());
  });
});

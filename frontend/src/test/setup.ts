import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(cleanup);

// jsdom lacks these browser APIs; stub them so animated components can render.
if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
      onchange: null,
    }) as MediaQueryList;
}
HTMLCanvasElement.prototype.getContext = (() => null) as never;

// Observers used by the libraries.dev effects (liquid-gooey, metal-fx, border-beam); jsdom has none.
class NoopObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return [];
  }
}
const browser = window as unknown as Record<string, unknown>;
browser.ResizeObserver ??= NoopObserver;
browser.IntersectionObserver ??= NoopObserver;

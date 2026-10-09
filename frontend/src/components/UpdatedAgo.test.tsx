import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PollingProvider } from "../lib/polling";
import { UpdatedAgo } from "./UpdatedAgo";

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-10-10T12:00:00Z"));
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

const at = (secondsAgo: number) => Date.now() - secondsAgo * 1000;

describe("UpdatedAgo", () => {
  it("shows how long ago the data was loaded and keeps counting", () => {
    render(
      <PollingProvider intervalMs={5000}>
        <UpdatedAgo updatedAt={at(30)} failed={false} />
      </PollingProvider>,
    );
    expect(screen.getByText("Actualizado hace 30 s")).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(35_000);
    });
    expect(screen.getByText("Actualizado hace 1 min")).toBeInTheDocument();
  });

  it("announces a failed refresh once, in a status region, and keeps the age out of it", () => {
    render(
      <PollingProvider intervalMs={5000}>
        <UpdatedAgo updatedAt={at(10)} failed />
      </PollingProvider>,
    );
    expect(screen.getByRole("status")).toHaveTextContent("No se pudo actualizar");
    expect(screen.getByRole("status")).not.toHaveTextContent("Actualizado hace");
  });

  it("renders nothing before the first load or when polling is off", () => {
    const { container, rerender } = render(
      <PollingProvider intervalMs={5000}>
        <UpdatedAgo updatedAt={null} failed={false} />
      </PollingProvider>,
    );
    expect(container).toBeEmptyDOMElement();
    rerender(<UpdatedAgo updatedAt={at(30)} failed={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("does not tick while the tab is hidden", () => {
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    render(
      <PollingProvider intervalMs={5000}>
        <UpdatedAgo updatedAt={at(10)} failed={false} />
      </PollingProvider>,
    );
    act(() => {
      vi.advanceTimersByTime(60_000);
    });
    expect(screen.getByText("Actualizado hace 10 s")).toBeInTheDocument();
  });
});

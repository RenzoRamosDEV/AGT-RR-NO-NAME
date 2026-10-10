import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ReviewAggregate } from "../data/mock";
import { StatusIcon } from "./StatusIcon";

describe("StatusIcon", () => {
  it.each([
    ["pending", "Pendiente", "warning"],
    ["running", "En curso", "warning"],
    ["partial_failed", "Fallo parcial", "warning"],
    ["failed", "Fallida", "danger"],
    ["completed", "Completada", "success"],
  ] as [ReviewAggregate, string, string][])(
    "%s is an image with the text alternative «%s» in the %s tone",
    (status, label, tone) => {
      render(<StatusIcon status={status} />);
      const icon = screen.getByRole("img", { name: label });
      expect(icon).toHaveAttribute("data-tone", tone);
    },
  );

  it("is decorative, with no image role, while the status is unknown", () => {
    const { container } = render(<StatusIcon status={undefined} />);
    expect(screen.queryByRole("img")).toBeNull();
    expect(container.firstElementChild).toHaveAttribute("aria-hidden", "true");
  });
});

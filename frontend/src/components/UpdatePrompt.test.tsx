import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { UpdatePrompt } from "./UpdatePrompt";

const registration = vi.hoisted(() => ({
  needRefresh: false,
  setNeedRefresh: vi.fn(),
  updateServiceWorker: vi.fn(),
}));

vi.mock("virtual:pwa-register/react", () => ({
  useRegisterSW: () => ({
    needRefresh: [registration.needRefresh, registration.setNeedRefresh],
    offlineReady: [false, vi.fn()],
    updateServiceWorker: registration.updateServiceWorker,
  }),
}));

describe("UpdatePrompt", () => {
  beforeEach(() => {
    registration.needRefresh = false;
    registration.setNeedRefresh.mockReset();
    registration.updateServiceWorker.mockReset();
  });

  it("renders nothing while the current version is up to date", () => {
    const { container } = render(<UpdatePrompt />);
    expect(container).toBeEmptyDOMElement();
  });

  it("announces the new version and reloads only when the user asks", async () => {
    registration.needRefresh = true;
    render(<UpdatePrompt />);
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("Nueva versión disponible.");
    expect(registration.updateServiceWorker).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Actualizar" }));
    expect(registration.updateServiceWorker).toHaveBeenCalledWith(true);
  });

  it("can be dismissed with the keyboard without updating", async () => {
    registration.needRefresh = true;
    render(<UpdatePrompt />);
    const user = userEvent.setup();
    await user.tab();
    await user.tab();
    expect(screen.getByRole("button", { name: "Cerrar" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(registration.setNeedRefresh).toHaveBeenCalledWith(false);
    expect(registration.updateServiceWorker).not.toHaveBeenCalled();
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AgentAvatar, agentLogo } from "./AgentAvatar";

describe("AgentAvatar with logos", () => {
  it("has a logo for Claude and Codex whatever the case, and none for other agents", () => {
    expect(agentLogo("claude")).toBeTruthy();
    expect(agentLogo("Codex")).toBeTruthy();
    expect(agentLogo("CLAUDE")).toBe(agentLogo("claude"));
    expect(agentLogo("claude")).not.toBe(agentLogo("codex"));
    expect(agentLogo("agent_1")).toBeUndefined();
  });

  it("shows the logo image for Claude and for Codex", () => {
    const { container, rerender } = render(<AgentAvatar agent="Claude" size={36} />);
    expect(container.querySelector("img")).toHaveAttribute("src", agentLogo("claude"));
    rerender(<AgentAvatar agent="codex" size={36} />);
    expect(container.querySelector("img")).toHaveAttribute("src", agentLogo("codex"));
    expect(container.firstElementChild).toHaveAttribute("data-kind", "logo");
  });

  it("shows the initials of an agent without a logo", () => {
    const { container } = render(<AgentAvatar agent="agent_1" />);
    expect(container.querySelector("img")).toBeNull();
    expect(container).toHaveTextContent("A1");
    expect(container.firstElementChild).toHaveAttribute("data-kind", "initials");
  });

  it("is decorative by default: hidden from assistive technology and with an empty alt", () => {
    const { container } = render(<AgentAvatar agent="claude" />);
    expect(container.firstElementChild).toHaveAttribute("aria-hidden", "true");
    expect(container.querySelector("img")).toHaveAttribute("alt", "");
  });

  it("names the agent in the alt when it stands alone", () => {
    render(<AgentAvatar agent="codex" decorative={false} />);
    expect(screen.getByRole("img", { name: "Codex" })).toBeInTheDocument();
  });

  it("names an agent without logo through the role when it stands alone", () => {
    render(<AgentAvatar agent="agent_2" decorative={false} />);
    expect(screen.getByRole("img", { name: "Agent_2" })).toHaveTextContent("A2");
  });

  it("loads lazily and sets its size on the box and on the image", () => {
    const { container } = render(<AgentAvatar agent="claude" size={20} />);
    const img = container.querySelector("img") as HTMLImageElement;
    expect(img).toHaveAttribute("loading", "lazy");
    expect(img).toHaveAttribute("decoding", "async");
    expect(img).toHaveAttribute("width", "20");
    expect(container.firstElementChild).toHaveStyle({ width: "20px", height: "20px" });
    expect(container.firstElementChild).toHaveAttribute("data-size", "20");
  });

  it("falls back to the initials when the logo fails to load", () => {
    const { container } = render(<AgentAvatar agent="claude" />);
    fireEvent.error(container.querySelector("img") as HTMLImageElement);
    expect(container.querySelector("img")).toBeNull();
    expect(container).toHaveTextContent("C");
    expect(container.firstElementChild).toHaveAttribute("data-kind", "initials");
  });

  it("does not carry a failed logo over to another agent", () => {
    const { container, rerender } = render(<AgentAvatar agent="claude" />);
    fireEvent.error(container.querySelector("img") as HTMLImageElement);
    rerender(<AgentAvatar agent="codex" />);
    expect(container.querySelector("img")).toHaveAttribute("src", agentLogo("codex"));
  });
});

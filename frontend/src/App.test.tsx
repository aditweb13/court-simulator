import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import App from "./App";

// Mock 3D Canvas in jsdom environment
vi.mock("./scene/CourtroomCanvas", () => ({
  CourtroomCanvas: () => <div data-testid="mock-courtroom-canvas">Canvas 3D Viewport</div>,
}));

// Mock API calls
vi.mock("./lib/api", () => ({
  fetchCases: vi.fn().mockResolvedValue([
    {
      id: "case_001",
      slug: "state-v-k-sharma",
      title: "State of Maharashtra v. K. Sharma",
      charge: "Section 103(1) BNS",
      jurisdiction: "Sessions Court",
      difficulty: "standard",
      summary: "Test case",
    },
  ]),
  getGuestToken: vi.fn().mockResolvedValue("mock-jwt-token"),
  createTrial: vi.fn().mockResolvedValue({
    id: "trial-1234",
    case_id: "case_001",
    mode: "spectator",
    state: "SETUP",
  }),
}));

describe("App Component", () => {
  it("renders the courtroom simulator header, canvas viewport, controls, and transcript", async () => {
    await act(async () => {
      render(<App />);
    });

    expect(screen.getByRole("heading", { name: "Verdict", level: 1 })).toBeInTheDocument();
    expect(screen.getByText(/Indian Courtroom Trial Simulator/i)).toBeInTheDocument();
    expect(screen.getByTestId("mock-courtroom-canvas")).toBeInTheDocument();
    expect(screen.getByText(/Courtroom Chambers — Live View/i)).toBeInTheDocument();
    expect(screen.getByText(/Trial Control Panel/i)).toBeInTheDocument();
    expect(screen.getByText(/Official Court Record/i)).toBeInTheDocument();
  });

  it("toggles theme between light and dark when theme button is clicked", async () => {
    await act(async () => {
      render(<App />);
    });

    const themeButton = screen.getByRole("button", { name: /Switch to dark theme/i });
    expect(themeButton).toBeInTheDocument();

    fireEvent.click(themeButton);
    expect(screen.getByRole("button", { name: /Switch to light theme/i })).toBeInTheDocument();
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");

    fireEvent.click(screen.getByRole("button", { name: /Switch to light theme/i }));
    expect(screen.getByRole("button", { name: /Switch to dark theme/i })).toBeInTheDocument();
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("toggles SFX button and opens disclaimer modal", async () => {
    await act(async () => {
      render(<App />);
    });

    const sfxBtn = screen.getByRole("button", { name: /Mute sound effects/i });
    expect(sfxBtn).toBeInTheDocument();
    fireEvent.click(sfxBtn);
    expect(screen.getByRole("button", { name: /Enable sound effects/i })).toBeInTheDocument();

    const disclaimerBtn = screen.getByRole("button", { name: /Legal Notice & Ethics Charter/i });
    expect(disclaimerBtn).toBeInTheDocument();
    fireEvent.click(disclaimerBtn);
    expect(screen.getByTestId("disclaimer-modal")).toBeInTheDocument();
  });
});

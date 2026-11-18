import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import App from "./App";

// Mock 3D Canvas in jsdom environment
vi.mock("./scene/CourtroomCanvas", () => ({
  CourtroomCanvas: () => <div data-testid="mock-courtroom-canvas">Canvas 3D Viewport</div>,
}));

describe("App Component", () => {
  it("renders the courtroom simulator header and canvas viewport", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Verdict", level: 1 })).toBeInTheDocument();
    expect(screen.getByText(/3D Courtroom Simulator/i)).toBeInTheDocument();
    expect(screen.getByTestId("mock-courtroom-canvas")).toBeInTheDocument();
    expect(screen.getByText(/Court In Session|Courtroom Chambers/i)).toBeInTheDocument();
  });

  it("toggles theme between light and dark when theme button is clicked", () => {
    render(<App />);

    const themeButton = screen.getByRole("button", { name: /Theme: Light/i });
    expect(themeButton).toBeInTheDocument();

    fireEvent.click(themeButton);
    expect(screen.getByRole("button", { name: /Theme: Dark/i })).toBeInTheDocument();
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");

    fireEvent.click(screen.getByRole("button", { name: /Theme: Dark/i }));
    expect(screen.getByRole("button", { name: /Theme: Light/i })).toBeInTheDocument();
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });
});

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DisclaimerModal } from "./DisclaimerModal";

describe("DisclaimerModal Component", () => {
  it("does not render when isOpen is false", () => {
    const { container } = render(<DisclaimerModal isOpen={false} onClose={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders when isOpen is true with legal notice and ethics charter", () => {
    render(<DisclaimerModal isOpen={true} onClose={vi.fn()} />);
    expect(screen.getByTestId("disclaimer-modal")).toBeInTheDocument();
    expect(screen.getByText(/legal notice, ethics charter & simulator scope/i)).toBeInTheDocument();
    expect(screen.getByText(/bharatiya nyaya sanhita, 2023/i)).toBeInTheDocument();
    expect(screen.getByText(/ethical ai charter & demographic neutrality/i)).toBeInTheDocument();
    expect(screen.getByText(/section 52\(1\)\(q\) indian copyright act compliance/i)).toBeInTheDocument();
  });

  it("calls onClose when acknowledge button is clicked", () => {
    const handleClose = vi.fn();
    render(<DisclaimerModal isOpen={true} onClose={handleClose} />);

    const ackBtn = screen.getByRole("button", { name: /i understand & acknowledge/i });
    fireEvent.click(ackBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when escape key is pressed", () => {
    const handleClose = vi.fn();
    render(<DisclaimerModal isOpen={true} onClose={handleClose} />);

    fireEvent.keyDown(window, { key: "Escape" });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});


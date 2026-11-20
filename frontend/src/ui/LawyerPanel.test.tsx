import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LawyerPanel } from "./LawyerPanel";
import { useTrialStore } from "../store/trialStore";
import { trialWs } from "../events/trialWs";

// Mock trialWs methods
vi.mock("../events/trialWs", () => ({
  trialWs: {
    sendHumanAction: vi.fn(),
    sendObjection: vi.fn(),
  },
}));

describe("LawyerPanel Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useTrialStore.getState().reset();
  });

  it("does not render when mode is spectator / watch", () => {
    useTrialStore.setState({ mode: "spectator" });
    const { container } = render(<LawyerPanel />);
    expect(container.firstChild).toBeNull();
  });

  it("renders when mode is lawyer", () => {
    useTrialStore.setState({ mode: "lawyer", isHumanTurn: false, objectionQuota: 3 });
    render(<LawyerPanel />);
    expect(screen.getByTestId("lawyer-panel")).toBeInTheDocument();
    expect(screen.getByText("Awaiting Floor...")).toBeInTheDocument();
    expect(screen.getByTestId("quota-display")).toHaveTextContent("3/3");
  });

  it("shows active turn indicator and enables controls when isHumanTurn is true", () => {
    useTrialStore.setState({
      mode: "lawyer",
      isHumanTurn: true,
      pendingPrompt: { type: "prompt", role: "prosecutor", options: ["examine", "pass"] },
    });
    render(<LawyerPanel />);
    expect(screen.getByText("Your Turn to Examine / Argue")).toBeInTheDocument();
    expect(screen.getByText("examine")).toBeInTheDocument();

    const textarea = screen.getByRole("textbox", { name: /question or argument/i });
    expect(textarea).not.toBeDisabled();
  });

  it("disables objection button when quota reaches 0", () => {
    useTrialStore.setState({ mode: "lawyer", objectionQuota: 0 });
    render(<LawyerPanel />);
    const objectionBtn = screen.getByTestId("objection-button");
    expect(objectionBtn).toBeDisabled();
    expect(objectionBtn).toHaveAttribute(
      "title",
      "Objection quota exhausted (0 remaining)",
    );
  });

  it("sends objection event and decrements quota when objection is lodged", () => {
    useTrialStore.setState({ mode: "lawyer", objectionQuota: 2 });
    render(<LawyerPanel />);

    const objectionBtn = screen.getByTestId("objection-button");
    fireEvent.click(objectionBtn);

    expect(screen.getByTestId("objection-window")).toBeInTheDocument();

    const lodgeBtn = screen.getByRole("button", { name: /lodge objection/i });
    fireEvent.click(lodgeBtn);

    expect(trialWs.sendObjection).toHaveBeenCalledWith("hearsay", undefined);
    expect(useTrialStore.getState().objectionQuota).toBe(1);
  });

  it("sends examine action when examine button is clicked with input", () => {
    useTrialStore.setState({ mode: "lawyer", isHumanTurn: true });
    render(<LawyerPanel />);

    const textarea = screen.getByRole("textbox", { name: /question or argument/i });
    fireEvent.change(textarea, { target: { value: "Where were you on the night of the incident?" } });

    const examineBtn = screen.getByRole("button", { name: /examine witness/i });
    fireEvent.click(examineBtn);

    expect(trialWs.sendHumanAction).toHaveBeenCalledWith(
      "examine",
      "Where were you on the night of the incident?",
      undefined,
    );
    expect(useTrialStore.getState().isHumanTurn).toBe(false);
  });
});


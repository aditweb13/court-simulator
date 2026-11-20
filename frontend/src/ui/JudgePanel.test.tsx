import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { JudgePanel } from "./JudgePanel";
import { useTrialStore } from "../store/trialStore";
import { trialWs } from "../events/trialWs";

vi.mock("../events/trialWs", () => ({
  trialWs: {
    sendHumanAction: vi.fn(),
    send: vi.fn(),
  },
}));

describe("JudgePanel Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useTrialStore.getState().reset();
  });

  it("does not render when mode is not judge", () => {
    useTrialStore.setState({ mode: "spectator" });
    const { container } = render(<JudgePanel />);
    expect(container.firstChild).toBeNull();
  });

  it("renders when mode is judge", () => {
    useTrialStore.setState({ mode: "judge" });
    render(<JudgePanel />);
    expect(screen.getByTestId("judge-panel")).toBeInTheDocument();
    expect(screen.getByText(/presiding magistrate bench/i)).toBeInTheDocument();
  });

  it("renders objection ruling buttons and sends sustain ruling", () => {
    useTrialStore.setState({
      mode: "judge",
      isHumanTurn: true,
      pendingPrompt: {
        type: "prompt",
        role: "judge",
        options: ["sustain", "overrule"],
      },
    });
    render(<JudgePanel />);

    const sustainBtn = screen.getByTestId("sustain-btn");
    expect(sustainBtn).toBeInTheDocument();

    fireEvent.click(sustainBtn);
    expect(trialWs.sendHumanAction).toHaveBeenCalledWith("sustain");
    expect(useTrialStore.getState().isHumanTurn).toBe(false);
  });

  it("renders verdict pronouncement and submits judicial decree", () => {
    useTrialStore.setState({
      mode: "judge",
      isHumanTurn: true,
      pendingPrompt: {
        type: "prompt",
        role: "judge",
        options: ["guilty", "not_guilty"],
      },
    });
    render(<JudgePanel />);

    expect(screen.getByText(/sessions court verdict pronouncement/i)).toBeInTheDocument();

    const submitBtn = screen.getByRole("button", { name: /enter judicial decree/i });
    fireEvent.click(submitBtn);

    expect(trialWs.send).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "human_action",
        action: "vote",
      }),
    );
  });
});

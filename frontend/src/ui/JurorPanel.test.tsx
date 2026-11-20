import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { JurorPanel } from "./JurorPanel";
import { useTrialStore } from "../store/trialStore";
import { trialWs } from "../events/trialWs";

vi.mock("../events/trialWs", () => ({
  trialWs: {
    sendHumanAction: vi.fn(),
    send: vi.fn(),
  },
}));

describe("JurorPanel Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useTrialStore.getState().reset();
  });

  it("does not render when mode is not juror", () => {
    useTrialStore.setState({ mode: "spectator" });
    const { container } = render(<JurorPanel />);
    expect(container.firstChild).toBeNull();
  });

  it("renders when mode is juror", () => {
    useTrialStore.setState({ mode: "juror" });
    render(<JurorPanel />);
    expect(screen.getByTestId("juror-panel")).toBeInTheDocument();
    expect(screen.getByText(/citizen juror box/i)).toBeInTheDocument();
  });

  it("submits ballot when voting is prompted", () => {
    useTrialStore.setState({
      mode: "juror",
      isHumanTurn: true,
      pendingPrompt: {
        type: "prompt",
        role: "juror",
        options: ["guilty", "not_guilty"],
      },
    });
    render(<JurorPanel />);

    expect(screen.getByText(/jury deliberation ballot/i)).toBeInTheDocument();

    const notGuiltyBtn = screen.getByTestId("vote-not-guilty-btn");
    fireEvent.click(notGuiltyBtn);

    const submitBtn = screen.getByRole("button", { name: /submit juror ballot/i });
    fireEvent.click(submitBtn);

    expect(trialWs.send).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "human_action",
        action: "vote",
      }),
    );
  });

  it("submits deliberation statement when prompted", () => {
    useTrialStore.setState({
      mode: "juror",
      isHumanTurn: true,
      pendingPrompt: {
        type: "prompt",
        role: "juror",
        options: ["deliberate", "pass"],
      },
    });
    render(<JurorPanel />);

    const textarea = screen.getByPlaceholderText(/speak to your fellow jurors/i);
    fireEvent.change(textarea, { target: { value: "The forensic chain of custody was broken." } });

    const addressBtn = screen.getByRole("button", { name: /address jurors/i });
    fireEvent.click(addressBtn);

    expect(trialWs.sendHumanAction).toHaveBeenCalledWith(
      "deliberate",
      "The forensic chain of custody was broken.",
    );
  });
});


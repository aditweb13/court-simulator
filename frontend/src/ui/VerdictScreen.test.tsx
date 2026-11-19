import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { VerdictScreen } from "./VerdictScreen";
import { useTrialStore } from "../store/trialStore";

describe("VerdictScreen Component", () => {
  beforeEach(() => {
    useTrialStore.setState({
      verdict: null,
      trialId: null,
    });
  });

  it("renders nothing when there is no verdict", () => {
    const { container } = render(<VerdictScreen />);
    expect(container.firstChild).toBeNull();
  });

  it("renders guilty verdict and score metrics when verdict event arrives", () => {
    useTrialStore.setState({
      verdict: {
        type: "verdict",
        outcome: "guilty",
        score: 0.829,
        threshold: 0.75,
        disagreement: 0.057,
        matches_truth: true,
        reasoning: "Guilty beyond reasonable doubt.",
      },
      trialId: "test-trial-123",
    });

    render(<VerdictScreen />);

    expect(screen.getByText(/Sessions Court Verdict Pronouncement/i)).toBeInTheDocument();
    expect(screen.getByText(/Guilty as Charged/i)).toBeInTheDocument();
    expect(screen.getByText(/Combined Guilt Score: 82.9%/i)).toBeInTheDocument();
    expect(screen.getByText(/Guilty beyond reasonable doubt./i)).toBeInTheDocument();
  });

  it("can dismiss the dialog and reopen with the floating button", () => {
    useTrialStore.setState({
      verdict: {
        type: "verdict",
        outcome: "not_guilty",
        score: 0.35,
        threshold: 0.75,
        disagreement: 0.1,
        matches_truth: true,
      },
      trialId: "test-trial-123",
    });

    render(<VerdictScreen />);

    expect(screen.getByText(/Acquitted & Discharged/i)).toBeInTheDocument();

    // Click dismiss button
    const closeBtn = screen.getByLabelText(/Dismiss verdict dialog/i);
    fireEvent.click(closeBtn);

    // Dialog is hidden, floating button appears
    expect(screen.queryByText(/Sessions Court Verdict Pronouncement/i)).toBeNull();
    const reopenBtn = screen.getByText(/View Final Verdict/i);
    expect(reopenBtn).toBeInTheDocument();

    // Reopen dialog
    fireEvent.click(reopenBtn);
    expect(screen.getByText(/Sessions Court Verdict Pronouncement/i)).toBeInTheDocument();
  });
});


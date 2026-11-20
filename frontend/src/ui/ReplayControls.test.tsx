import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ReplayControls } from "./ReplayControls";
import { useTrialStore } from "../store/trialStore";
import * as api from "../lib/api";

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual<typeof api>("../lib/api");
  return {
    ...actual,
    fetchTrialTurns: vi.fn(),
  };
});

describe("ReplayControls Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useTrialStore.getState().reset();
  });

  it("renders replay controls panel and input", () => {
    render(<ReplayControls />);
    expect(screen.getByTestId("replay-controls")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/paste trial uuid/i)).toBeInTheDocument();
  });

  it("loads turns and enables transport controls when trial turns are fetched", async () => {
    const mockTurns = [
      {
        id: "turn-1",
        seq: 1,
        speaker: "judge",
        text: "Sessions court is in session.",
        struck: false,
      },
      {
        id: "turn-2",
        seq: 2,
        speaker: "prosecutor",
        text: "The State presents its opening case.",
        struck: false,
      },
    ];

    vi.mocked(api.fetchTrialTurns).mockResolvedValue(mockTurns);

    render(<ReplayControls />);
    const input = screen.getByPlaceholderText(/paste trial uuid/i);
    fireEvent.change(input, { target: { value: "trial-1234" } });

    const loadBtn = screen.getByRole("button", { name: /load recording/i });
    fireEvent.click(loadBtn);

    await waitFor(() => {
      expect(screen.getByText(/turn 1 of 2/i)).toBeInTheDocument();
    });

    const playBtn = screen.getByTestId("replay-play-button");
    expect(playBtn).toBeInTheDocument();
    expect(playBtn).toHaveTextContent(/▶ play/i);
  });

  it("toggles play and pause on transport control click", async () => {
    const mockTurns = [
      { id: "turn-1", seq: 1, speaker: "judge", text: "Line 1", struck: false },
      { id: "turn-2", seq: 2, speaker: "defense", text: "Line 2", struck: false },
    ];
    vi.mocked(api.fetchTrialTurns).mockResolvedValue(mockTurns);

    render(<ReplayControls />);
    const loadBtn = screen.getByRole("button", { name: /load recording/i });
    fireEvent.change(screen.getByPlaceholderText(/paste trial uuid/i), {
      target: { value: "trial-abc" },
    });
    fireEvent.click(loadBtn);

    await waitFor(() => {
      expect(screen.getByTestId("replay-play-button")).toBeInTheDocument();
    });

    const playBtn = screen.getByTestId("replay-play-button");
    fireEvent.click(playBtn);
    expect(playBtn).toHaveTextContent(/⏸ pause/i);

    fireEvent.click(playBtn);
    expect(playBtn).toHaveTextContent(/▶ play/i);
  });
});


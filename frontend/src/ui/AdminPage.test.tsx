import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { AdminPage } from "./AdminPage";
import * as api from "../lib/api";

vi.mock("../lib/api", () => ({
  fetchLLMStatus: vi.fn(),
  getGuestToken: vi.fn().mockResolvedValue("mock-guest-token"),
}));

describe("AdminPage Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("displays loading skeleton while fetching LLM pool status", async () => {
    // Return promise that does not resolve immediately
    vi.mocked(api.fetchLLMStatus).mockReturnValue(new Promise(() => {}));

    render(<AdminPage />);
    expect(screen.getByTestId("admin-loading")).toBeInTheDocument();
    expect(screen.getByLabelText("Loading LLM pool status")).toBeInTheDocument();
  });

  it("displays error message and Retry button on failure per Design.md", async () => {
    vi.mocked(api.fetchLLMStatus).mockRejectedValue(new Error("Admin privileges required"));

    await act(async () => {
      render(<AdminPage />);
    });

    await waitFor(() => {
      expect(screen.getByTestId("admin-error")).toBeInTheDocument();
    });

    expect(screen.getByText(/Access Restricted or Service Unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/Admin privileges required/i)).toBeInTheDocument();

    const retryBtn = screen.getByRole("button", { name: /retry/i });
    expect(retryBtn).toBeInTheDocument();

    // Verify retry button re-triggers API call
    vi.mocked(api.fetchLLMStatus).mockResolvedValueOnce([]);
    await act(async () => {
      fireEvent.click(retryBtn);
    });

    expect(api.fetchLLMStatus).toHaveBeenCalledTimes(2);
  });

  it("displays 'No LLM calls yet' empty state when call count is zero per Design.md", async () => {
    vi.mocked(api.fetchLLMStatus).mockResolvedValue([
      {
        provider: "groq",
        total_keys: 1,
        ready_keys: 1,
        cooling_keys: 0,
        keys: [
          {
            key_alias: "groq#1",
            provider: "groq",
            is_ready: true,
            cooling_down_seconds: 0.0,
            fail_count: 0,
            last_status: null,
            recent_call_count: 0,
          },
        ],
      },
    ]);

    await act(async () => {
      render(<AdminPage />);
    });

    await waitFor(() => {
      expect(screen.getByTestId("admin-empty")).toBeInTheDocument();
    });

    expect(screen.getByText("No LLM calls yet")).toBeInTheDocument();
    expect(screen.getByText(/no trial inferences or model calls have been recorded/i)).toBeInTheDocument();
  });

  it("displays complete provider metrics and key health breakdown when calls exist", async () => {
    vi.mocked(api.fetchLLMStatus).mockResolvedValue([
      {
        provider: "gemini",
        total_keys: 2,
        ready_keys: 1,
        cooling_keys: 1,
        keys: [
          {
            key_alias: "gemini#1",
            provider: "gemini",
            is_ready: true,
            cooling_down_seconds: 0.0,
            fail_count: 0,
            last_status: "ok",
            recent_call_count: 42,
          },
          {
            key_alias: "gemini#2",
            provider: "gemini",
            is_ready: false,
            cooling_down_seconds: 48.5,
            fail_count: 2,
            last_status: "quota",
            recent_call_count: 5,
          },
        ],
      },
    ]);

    await act(async () => {
      render(<AdminPage />);
    });

    await waitFor(() => {
      expect(screen.getByTestId("admin-content")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "System Administration", level: 1 })).toBeInTheDocument();
    expect(screen.getByText(/gemini pool/i)).toBeInTheDocument();
    expect(screen.getByText("gemini#1")).toBeInTheDocument();
    expect(screen.getByText("gemini#2")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText(/Cooling \(49s remaining\)/i)).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });
});

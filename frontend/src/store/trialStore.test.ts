import { describe, it, expect, beforeEach, vi } from "vitest";
import { useTrialStore } from "./trialStore";
import { LineEvent, StateEvent, VerdictEvent } from "../events/schemas";

describe("Trial Store (Zustand)", () => {
  beforeEach(() => {
    useTrialStore.getState().reset();
  });

  it("initializes with default state", () => {
    const state = useTrialStore.getState();
    expect(state.trialId).toBeNull();
    expect(state.status).toBe("idle");
    expect(state.trialState).toBe("IDLE");
    expect(state.currentLine).toBeNull();
    expect(state.currentCameraShot).toBe("wide");
    expect(state.transcript).toHaveLength(0);
    expect(state.eventQueue).toHaveLength(0);
  });

  it("handles state event", () => {
    const event: StateEvent = {
      type: "state",
      state: "OPENINGS",
    };
    useTrialStore.getState().handleServerEvent(event);
    expect(useTrialStore.getState().trialState).toBe("OPENINGS");
  });

  it("plays line event immediately if no active line", () => {
    const line: LineEvent = {
      type: "line",
      seq: 1,
      speaker: "judge",
      text: "The court is now in session.",
      camera: "judge",
      action: "talk",
    };

    const mockSendAck = vi.fn();
    useTrialStore.getState().handleServerEvent(line, mockSendAck);

    const state = useTrialStore.getState();
    expect(state.currentLine).toEqual(line);
    expect(state.activeSpeaker).toBe("judge");
    expect(state.activeAction).toBe("talk");
    expect(state.currentCameraShot).toBe("judge");
    expect(state.status).toBe("running");
    expect(state.transcript).toHaveLength(1);
  });

  it("queues subsequent lines while a line is playing", () => {
    const line1: LineEvent = {
      type: "line",
      seq: 1,
      speaker: "judge",
      text: "Court is seated.",
    };
    const line2: LineEvent = {
      type: "line",
      seq: 2,
      speaker: "clerk",
      text: "Matter number one.",
    };

    useTrialStore.getState().handleServerEvent(line1);
    useTrialStore.getState().handleServerEvent(line2);

    const state = useTrialStore.getState();
    expect(state.currentLine?.seq).toBe(1);
    expect(state.eventQueue).toHaveLength(1);
    expect(state.eventQueue[0].seq).toBe(2);

    // Acknowledge line 1 -> line 2 becomes active
    const mockSendAck = vi.fn();
    state.acknowledgeCurrentLine(mockSendAck);

    const updated = useTrialStore.getState();
    expect(mockSendAck).toHaveBeenCalledWith(1);
    expect(updated.currentLine?.seq).toBe(2);
    expect(updated.eventQueue).toHaveLength(0);
    expect(updated.transcript).toHaveLength(2);
  });

  it("handles verdict event", () => {
    const verdict: VerdictEvent = {
      type: "verdict",
      outcome: "guilty",
      score: 0.82,
      threshold: 0.75,
      disagreement: 0.1,
      matches_truth: true,
      reasoning: "Guilt established beyond reasonable doubt.",
    };

    useTrialStore.getState().handleServerEvent(verdict);

    const state = useTrialStore.getState();
    expect(state.verdict).toEqual(verdict);
    expect(state.status).toBe("completed");
    expect(state.trialState).toBe("VERDICT");
    expect(state.currentCameraShot).toBe("jury");
  });
});


import { create } from "zustand";
import { LineEvent, RulingEvent, ServerEvent, VerdictEvent } from "../events/schemas";
import { getShotForSpeaker, ShotName } from "../camera/shots";

export type TrialStatus =
  | "idle"
  | "connecting"
  | "running"
  | "paused"
  | "completed"
  | "error";

export interface TrialState {
  trialId: string | null;
  caseId: string | null;
  trialState: string;
  status: TrialStatus;
  error: string | null;
  currentLine: LineEvent | null;
  activeSpeaker: string | null;
  activeAction: string | null;
  currentCameraShot: ShotName;
  eventQueue: LineEvent[];
  transcript: (LineEvent | RulingEvent)[];
  verdict: VerdictEvent | null;
  autoAck: boolean;
  minReadingTimeMs: number;

  // Actions
  setTrialId: (trialId: string | null) => void;
  setCaseId: (caseId: string | null) => void;
  setStatus: (status: TrialStatus) => void;
  setError: (error: string | null) => void;
  setAutoAck: (autoAck: boolean) => void;
  setCameraShot: (shot: ShotName) => void;
  handleServerEvent: (
    event: ServerEvent,
    sendAck?: (seq: number) => void,
  ) => void;
  acknowledgeCurrentLine: (sendAck?: (seq: number) => void) => void;
  reset: () => void;
}

export const useTrialStore = create<TrialState>((set, get) => ({
  trialId: null,
  caseId: null,
  trialState: "IDLE",
  status: "idle",
  error: null,
  currentLine: null,
  activeSpeaker: null,
  activeAction: null,
  currentCameraShot: "wide",
  eventQueue: [],
  transcript: [],
  verdict: null,
  autoAck: true,
  minReadingTimeMs: 2000,

  setTrialId: (trialId) => set({ trialId }),
  setCaseId: (caseId) => set({ caseId }),
  setStatus: (status) => set({ status }),
  setError: (error) => set({ error, status: error ? "error" : get().status }),
  setAutoAck: (autoAck) => set({ autoAck }),
  setCameraShot: (shot) => set({ currentCameraShot: shot }),

  handleServerEvent: (event: ServerEvent, sendAck?: (seq: number) => void) => {
    switch (event.type) {
      case "state": {
        set({ trialState: event.state });
        break;
      }

      case "line": {
        const shot = getShotForSpeaker(event.camera || event.speaker).name;
        const current = get().currentLine;

        // If no line is currently playing, play this line immediately
        if (!current) {
          set((state) => ({
            currentLine: event,
            activeSpeaker: event.speaker,
            activeAction: event.action || null,
            currentCameraShot: shot,
            status: "running",
            transcript: [...state.transcript, event],
          }));

          if (get().autoAck && sendAck) {
            // Dynamic pacing: ~35ms per character, clamped between minReadingTimeMs and 6000ms
            const delay = Math.min(
              Math.max(event.text.length * 35, get().minReadingTimeMs),
              6000,
            );
            setTimeout(() => {
              sendAck(event.seq);
            }, delay);
          }
        } else {
          // Add to queue to play sequentially
          set((state) => ({
            eventQueue: [...state.eventQueue, event],
          }));
        }
        break;
      }

      case "ruling": {
        set((state) => ({
          transcript: [...state.transcript, event],
        }));
        break;
      }

      case "verdict": {
        set({
          verdict: event,
          status: "completed",
          trialState: "VERDICT",
          currentCameraShot: "jury",
        });
        break;
      }

      case "error": {
        set({
          error: event.message,
          status: "error",
        });
        break;
      }
    }
  },

  acknowledgeCurrentLine: (sendAck?: (seq: number) => void) => {
    const { currentLine, eventQueue, autoAck, minReadingTimeMs } = get();
    if (!currentLine) return;

    if (sendAck) {
      sendAck(currentLine.seq);
    }

    // Play next event from queue if available
    if (eventQueue.length > 0) {
      const nextLine = eventQueue[0];
      const remainingQueue = eventQueue.slice(1);
      const shot = getShotForSpeaker(nextLine.camera || nextLine.speaker).name;

      set((state) => ({
        currentLine: nextLine,
        activeSpeaker: nextLine.speaker,
        activeAction: nextLine.action || null,
        currentCameraShot: shot,
        eventQueue: remainingQueue,
        transcript: [...state.transcript, nextLine],
      }));

      if (autoAck && sendAck) {
        const delay = Math.min(
          Math.max(nextLine.text.length * 35, minReadingTimeMs),
          6000,
        );
        setTimeout(() => {
          sendAck(nextLine.seq);
        }, delay);
      }
    } else {
      set({
        currentLine: null,
        activeSpeaker: null,
        activeAction: null,
      });
    }
  },

  reset: () =>
    set({
      trialId: null,
      caseId: null,
      trialState: "IDLE",
      status: "idle",
      error: null,
      currentLine: null,
      activeSpeaker: null,
      activeAction: null,
      currentCameraShot: "wide",
      eventQueue: [],
      transcript: [],
      verdict: null,
    }),
}));

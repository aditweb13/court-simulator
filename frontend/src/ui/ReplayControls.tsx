import { useState, useEffect, useRef } from "react";
import { cn } from "../lib/utils";
import { useTrialStore } from "../store/trialStore";
import { fetchTrialTurns, TurnSummary } from "../lib/api";
import { LineEvent } from "../events/schemas";
import { getShotForSpeaker } from "../camera/shots";
import { browserTTS } from "../audio/tts";

interface ReplayControlsProps {
  className?: string;
  onClose?: () => void;
}

export function ReplayControls({ className, onClose }: ReplayControlsProps) {
  const currentTrialId = useTrialStore((state) => state.trialId);

  const [inputTrialId, setInputTrialId] = useState<string>(currentTrialId || "");
  const [turns, setTurns] = useState<TurnSummary[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number>(-1);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speed, setSpeed] = useState<number>(1.0);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const playTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const applyTurnToStore = (
    turn: TurnSummary,
    accumulatedTurns: TurnSummary[],
  ) => {
    const shot = getShotForSpeaker(turn.speaker).name;
    const lineEvt: LineEvent = {
      type: "line",
      seq: turn.seq,
      speaker: turn.speaker,
      text: turn.text,
      action: turn.action,
      emotion: turn.emotion,
      camera: shot,
    };

    const transcriptItems: LineEvent[] = accumulatedTurns.map((t) => ({
      type: "line",
      seq: t.seq,
      speaker: t.speaker,
      text: t.text,
      action: t.action,
      emotion: t.emotion,
      camera: getShotForSpeaker(t.speaker).name,
    }));

    useTrialStore.setState({
      currentLine: lineEvt,
      activeSpeaker: turn.speaker,
      activeAction: turn.action || null,
      currentCameraShot: shot,
      transcript: transcriptItems,
      status: "running",
      trialState: turn.phase || "PROCEEDINGS",
    });

    if (useTrialStore.getState().ttsEnabled) {
      browserTTS.speak(turn.speaker, turn.text);
    }
  };

  // Handle step to specific index
  const goToIndex = (idx: number) => {
    if (idx < 0 || idx >= turns.length) return;
    setCurrentIndex(idx);
    applyTurnToStore(turns[idx], turns.slice(0, idx + 1));
  };

  // Step forward
  const handleStepForward = () => {
    if (currentIndex < turns.length - 1) {
      goToIndex(currentIndex + 1);
    } else {
      setIsPlaying(false);
    }
  };

  // Step backward
  const handleStepBackward = () => {
    if (currentIndex > 0) {
      goToIndex(currentIndex - 1);
    }
  };

  // Play / Pause toggle
  const handleTogglePlay = () => {
    if (turns.length === 0) return;
    if (currentIndex >= turns.length - 1) {
      goToIndex(0);
    }
    setIsPlaying((prev) => !prev);
  };

  const loadTrialTurns = async (idToLoad: string) => {
    if (!idToLoad.trim()) return;
    setLoading(true);
    setError(null);
    setIsPlaying(false);

    try {
      const data = await fetchTrialTurns(idToLoad.trim(), { limit: 500 });
      if (!data || data.length === 0) {
        setError("No recorded dialogue turns found for this trial ID.");
        setTurns([]);
        setCurrentIndex(-1);
      } else {
        setTurns(data);
        setCurrentIndex(0);
        applyTurnToStore(data[0], data.slice(0, 1));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load trial turns");
      setTurns([]);
      setCurrentIndex(-1);
    } finally {
      setLoading(false);
    }
  };

  // Paced playback timer loop
  useEffect(() => {
    if (!isPlaying || turns.length === 0 || currentIndex >= turns.length - 1) {
      if (playTimerRef.current) clearTimeout(playTimerRef.current);
      return;
    }

    const currentTurn = turns[currentIndex];
    const duration = Math.max(
      1000,
      Math.min((currentTurn?.text.length || 30) * 45, 6000),
    );
    const delay = duration / speed;

    playTimerRef.current = setTimeout(() => {
      if (currentIndex < turns.length - 1) {
        goToIndex(currentIndex + 1);
      } else {
        setIsPlaying(false);
      }
    }, delay);

    return () => {
      if (playTimerRef.current) clearTimeout(playTimerRef.current);
    };
  });

  return (
    <div
      data-testid="replay-controls"
      className={cn(
        "bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] p-4 shadow-sm space-y-3",
        className,
      )}
    >
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-2.5">
        <div className="flex items-center gap-2">
          <span className="font-serif font-semibold text-sm text-[var(--primary)]">
            Courtroom Chamber Replay
          </span>
          <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 border border-amber-500/30">
            Recorded Session
          </span>
        </div>

        {onClose && (
          <button
            onClick={onClose}
            className="text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer"
          >
            ✕ Close Replay
          </button>
        )}
      </div>

      {/* Trial ID loader input */}
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Paste Trial UUID to replay..."
          value={inputTrialId}
          onChange={(e) => setInputTrialId(e.target.value)}
          className="flex-1 px-3 py-1.5 text-xs font-mono bg-[var(--background)] border border-[var(--border)] rounded-[var(--radius-sm)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
        />
        <button
          onClick={() => loadTrialTurns(inputTrialId)}
          disabled={loading || !inputTrialId.trim()}
          className="px-3 py-1.5 text-xs font-medium bg-[var(--primary)] text-white rounded-[var(--radius-sm)] hover:brightness-110 disabled:opacity-50 cursor-pointer"
        >
          {loading ? "Loading..." : "Load Recording"}
        </button>
      </div>

      {error && (
        <div className="p-2 text-xs text-[var(--destructive)] bg-[var(--destructive)]/10 rounded border border-[var(--destructive)]/30">
          {error}
        </div>
      )}

      {turns.length > 0 && (
        <div className="space-y-2 pt-1">
          {/* Progress Slider */}
          <div className="space-y-1">
            <div className="flex justify-between text-[11px] text-[var(--text-secondary)] font-mono">
              <span>
                Turn {currentIndex + 1} of {turns.length}
              </span>
              <span>
                {turns[currentIndex]?.speaker.toUpperCase() || "RECORD"}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={turns.length - 1}
              value={currentIndex >= 0 ? currentIndex : 0}
              onChange={(e) => goToIndex(Number(e.target.value))}
              className="w-full h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-[var(--primary)]"
              aria-label="Replay turn scrubber"
            />
          </div>

          {/* Transport Controls */}
          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => goToIndex(0)}
                title="Restart from beginning"
                className="px-2 py-1 text-xs border border-[var(--border)] rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer"
              >
                ⏮
              </button>
              <button
                type="button"
                onClick={handleStepBackward}
                disabled={currentIndex <= 0}
                title="Step backward"
                className="px-2.5 py-1 text-xs border border-[var(--border)] rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 disabled:opacity-40 cursor-pointer"
              >
                ◀
              </button>
              <button
                type="button"
                data-testid="replay-play-button"
                onClick={handleTogglePlay}
                title={isPlaying ? "Pause replay" : "Play replay"}
                className={cn(
                  "px-4 py-1 text-xs font-semibold rounded text-white transition-all cursor-pointer",
                  isPlaying
                    ? "bg-amber-600 hover:bg-amber-700"
                    : "bg-[var(--primary)] hover:brightness-110",
                )}
              >
                {isPlaying ? "⏸ Pause" : "▶ Play"}
              </button>
              <button
                type="button"
                onClick={handleStepForward}
                disabled={currentIndex >= turns.length - 1}
                title="Step forward"
                className="px-2.5 py-1 text-xs border border-[var(--border)] rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 disabled:opacity-40 cursor-pointer"
              >
                ▶
              </button>
            </div>

            {/* Speed Multipliers */}
            <div className="flex items-center gap-1">
              <span className="text-[10px] text-[var(--text-secondary)] mr-1">Speed:</span>
              {[0.5, 1.0, 2.0].map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setSpeed(s)}
                  className={cn(
                    "px-1.5 py-0.5 text-[10px] font-mono rounded border transition-colors cursor-pointer",
                    speed === s
                      ? "bg-[var(--primary)] text-white border-transparent font-bold"
                      : "border-[var(--border)] text-[var(--text-secondary)] hover:bg-neutral-100 dark:hover:bg-neutral-800",
                  )}
                >
                  {s}x
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

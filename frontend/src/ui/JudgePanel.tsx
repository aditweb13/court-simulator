import { useState } from "react";
import { cn } from "../lib/utils";
import { useTrialStore } from "../store/trialStore";
import { trialWs } from "../events/trialWs";

interface JudgePanelProps {
  className?: string;
}

export function JudgePanel({ className }: JudgePanelProps) {
  const mode = useTrialStore((state) => state.mode);
  const pendingPrompt = useTrialStore((state) => state.pendingPrompt);
  const isHumanTurn = useTrialStore((state) => state.isHumanTurn);
  const setIsHumanTurn = useTrialStore((state) => state.setIsHumanTurn);

  const [guiltySelection, setGuiltySelection] = useState<boolean>(true);
  const [guiltProbability, setGuiltProbability] = useState<number>(0.85);
  const [judicialReasoning, setJudicialReasoning] = useState<string>("");

  if (mode !== "judge") {
    return null;
  }

  const isObjectionRulingPrompt =
    pendingPrompt?.options?.includes("sustain") &&
    pendingPrompt?.options?.includes("overrule");

  const isVerdictPrompt =
    pendingPrompt?.options?.includes("guilty") &&
    pendingPrompt?.options?.includes("not_guilty");

  const handleRuling = (decision: "sustain" | "overrule") => {
    trialWs.sendHumanAction(decision);
    setIsHumanTurn(false);
  };

  const handleVerdictSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    trialWs.send({
      type: "human_action",
      action: "vote",
      text: judicialReasoning.trim() || undefined,
      target: undefined,
    });
    setIsHumanTurn(false);
  };

  return (
    <div
      data-testid="judge-panel"
      className={cn(
        "bg-[var(--surface)] border border-amber-600/40 rounded-[var(--radius-lg)] p-4 shadow-md space-y-4",
        className,
      )}
    >
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-2.5">
        <div className="flex items-center gap-2">
          <span className="text-lg">⚖</span>
          <div>
            <h4 className="font-serif font-bold text-sm text-[var(--primary)]">
              Presiding Magistrate Bench
            </h4>
            <p className="text-[11px] text-[var(--text-secondary)]">
              Judicial direction and statutory admissibility rulings under BNSS & BSA
            </p>
          </div>
        </div>

        <span
          className={cn(
            "px-2 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider",
            isHumanTurn
              ? "bg-[var(--success)]/10 text-[var(--success)] animate-pulse"
              : "bg-neutral-100 dark:bg-neutral-800 text-[var(--text-secondary)]",
          )}
        >
          {isHumanTurn ? "Decision Required" : "Hearing Proceedings"}
        </span>
      </div>

      {/* Objection Ruling Floor */}
      {isObjectionRulingPrompt && (
        <div className="p-3.5 bg-amber-500/10 border border-amber-500/30 rounded-[var(--radius-md)] space-y-3">
          <div>
            <h5 className="font-bold text-xs uppercase tracking-wide text-amber-800 dark:text-amber-300">
              Objection Raised by Counsel
            </h5>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Evaluate statutory admissibility and rule from the bench:
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              data-testid="sustain-btn"
              onClick={() => handleRuling("sustain")}
              className="flex-1 py-2 text-xs font-bold text-white bg-[var(--destructive)] rounded-[var(--radius-md)] hover:brightness-110 active:brightness-95 transition-all shadow-sm cursor-pointer"
            >
              Sustain (Strike Testimony)
            </button>
            <button
              type="button"
              data-testid="overrule-btn"
              onClick={() => handleRuling("overrule")}
              className="flex-1 py-2 text-xs font-bold text-white bg-[var(--primary)] rounded-[var(--radius-md)] hover:brightness-110 active:brightness-95 transition-all shadow-sm cursor-pointer"
            >
              Overrule (Witness Must Answer)
            </button>
          </div>
        </div>
      )}

      {/* Verdict Pronouncement Floor */}
      {isVerdictPrompt && (
        <form onSubmit={handleVerdictSubmit} className="space-y-3">
          <div>
            <h5 className="font-bold text-xs uppercase tracking-wide text-[var(--primary)]">
              Sessions Court Verdict Pronouncement
            </h5>
            <p className="text-xs text-[var(--text-secondary)]">
              Deliver your judicial determination beyond all reasonable doubt.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setGuiltySelection(true)}
              className={cn(
                "py-2 text-xs font-bold rounded-[var(--radius-md)] border transition-all cursor-pointer",
                guiltySelection
                  ? "bg-[var(--destructive)] text-white border-transparent shadow-sm"
                  : "border-[var(--border)] text-[var(--text-secondary)] hover:bg-neutral-100 dark:hover:bg-neutral-800",
              )}
            >
              Determine: GUILTY
            </button>
            <button
              type="button"
              onClick={() => setGuiltySelection(false)}
              className={cn(
                "py-2 text-xs font-bold rounded-[var(--radius-md)] border transition-all cursor-pointer",
                !guiltySelection
                  ? "bg-[var(--success)] text-white border-transparent shadow-sm"
                  : "border-[var(--border)] text-[var(--text-secondary)] hover:bg-neutral-100 dark:hover:bg-neutral-800",
              )}
            >
              Determine: NOT GUILTY
            </button>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-xs text-[var(--text-secondary)] font-mono">
              <span>Judicial Probability:</span>
              <span className="font-bold">
                {Math.round(guiltProbability * 100)}%
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={Math.round(guiltProbability * 100)}
              onChange={(e) => setGuiltProbability(Number(e.target.value) / 100)}
              className="w-full h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-[var(--primary)]"
            />
          </div>

          <div>
            <label
              htmlFor="judicial-reasoning"
              className="block text-xs font-medium text-[var(--text-secondary)] mb-1"
            >
              Judicial Reasoning / Statutory Ratio:
            </label>
            <textarea
              id="judicial-reasoning"
              rows={2}
              value={judicialReasoning}
              onChange={(e) => setJudicialReasoning(e.target.value)}
              placeholder="Record findings of fact and statutory grounds..."
              className="w-full px-3 py-1.5 text-xs bg-[var(--background)] border border-[var(--border)] rounded-[var(--radius-sm)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] resize-none"
            />
          </div>

          <button
            type="submit"
            className="w-full py-2 text-xs font-semibold text-white bg-[var(--primary)] rounded-[var(--radius-md)] hover:brightness-110 active:brightness-95 transition-all shadow-sm cursor-pointer"
          >
            Enter Judicial Decree & Pronounce Verdict
          </button>
        </form>
      )}

      {!isObjectionRulingPrompt && !isVerdictPrompt && (
        <div className="p-3 text-xs text-[var(--text-secondary)] bg-black/5 dark:bg-white/5 rounded text-center">
          Court is hearing examination and argument. You will be prompted when an objection or verdict is placed before the Bench.
        </div>
      )}
    </div>
  );
}


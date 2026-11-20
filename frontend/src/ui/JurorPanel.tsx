import { useState } from "react";
import { cn } from "../lib/utils";
import { useTrialStore } from "../store/trialStore";
import { trialWs } from "../events/trialWs";

interface JurorPanelProps {
  className?: string;
}

export function JurorPanel({ className }: JurorPanelProps) {
  const mode = useTrialStore((state) => state.mode);
  const pendingPrompt = useTrialStore((state) => state.pendingPrompt);
  const isHumanTurn = useTrialStore((state) => state.isHumanTurn);
  const setIsHumanTurn = useTrialStore((state) => state.setIsHumanTurn);

  const [guiltyVote, setGuiltyVote] = useState<boolean>(true);
  const [guiltProbability, setGuiltProbability] = useState<number>(0.75);
  const [reasoning, setReasoning] = useState<string>("");
  const [deliberationStatement, setDeliberationStatement] = useState<string>("");

  if (mode !== "juror") {
    return null;
  }

  const isVotePrompt =
    pendingPrompt?.options?.includes("guilty") &&
    pendingPrompt?.options?.includes("not_guilty");

  const isDeliberationPrompt =
    pendingPrompt?.options?.includes("deliberate") ||
    pendingPrompt?.options?.includes("pass");

  const handleVoteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    trialWs.send({
      type: "human_action",
      action: "vote",
      text: reasoning.trim() || undefined,
      target: undefined,
    });
    setIsHumanTurn(false);
  };

  const handleDeliberateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!deliberationStatement.trim()) return;

    trialWs.sendHumanAction("deliberate", deliberationStatement.trim());
    setDeliberationStatement("");
    setIsHumanTurn(false);
  };

  const handlePassDeliberation = () => {
    trialWs.sendHumanAction("pass");
    setIsHumanTurn(false);
  };

  return (
    <div
      data-testid="juror-panel"
      className={cn(
        "bg-[var(--surface)] border border-blue-600/40 rounded-[var(--radius-lg)] p-4 shadow-md space-y-4",
        className,
      )}
    >
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-2.5">
        <div className="flex items-center gap-2">
          <span className="text-lg">👥</span>
          <div>
            <h4 className="font-serif font-bold text-sm text-[var(--primary)]">
              Citizen Juror Box (Seat #1)
            </h4>
            <p className="text-[11px] text-[var(--text-secondary)]">
              Evaluate evidence, weigh credibility, and deliberate with peers
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
          {isHumanTurn ? "Your Vote / Turn" : "Observing Record"}
        </span>
      </div>

      {/* Juror Ballot / Voting Floor */}
      {isVotePrompt && (
        <form onSubmit={handleVoteSubmit} className="space-y-3">
          <div>
            <h5 className="font-bold text-xs uppercase tracking-wide text-[var(--primary)]">
              Jury Deliberation Ballot
            </h5>
            <p className="text-xs text-[var(--text-secondary)]">
              Cast your vote on the guilt of the accused.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              data-testid="vote-guilty-btn"
              onClick={() => setGuiltyVote(true)}
              className={cn(
                "py-2 text-xs font-bold rounded-[var(--radius-md)] border transition-all cursor-pointer",
                guiltyVote
                  ? "bg-[var(--destructive)] text-white border-transparent shadow-sm"
                  : "border-[var(--border)] text-[var(--text-secondary)] hover:bg-neutral-100 dark:hover:bg-neutral-800",
              )}
            >
              GUILTY
            </button>
            <button
              type="button"
              data-testid="vote-not-guilty-btn"
              onClick={() => setGuiltyVote(false)}
              className={cn(
                "py-2 text-xs font-bold rounded-[var(--radius-md)] border transition-all cursor-pointer",
                !guiltyVote
                  ? "bg-[var(--success)] text-white border-transparent shadow-sm"
                  : "border-[var(--border)] text-[var(--text-secondary)] hover:bg-neutral-100 dark:hover:bg-neutral-800",
              )}
            >
              NOT GUILTY
            </button>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-xs text-[var(--text-secondary)] font-mono">
              <span>Assessment Confidence:</span>
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
              htmlFor="juror-reasoning"
              className="block text-xs font-medium text-[var(--text-secondary)] mb-1"
            >
              Reasoning / Crucial Factors:
            </label>
            <textarea
              id="juror-reasoning"
              rows={2}
              value={reasoning}
              onChange={(e) => setReasoning(e.target.value)}
              placeholder="What convinced you? (e.g. lack of alibi, reliable eyewitness...)"
              className="w-full px-3 py-1.5 text-xs bg-[var(--background)] border border-[var(--border)] rounded-[var(--radius-sm)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] resize-none"
            />
          </div>

          <button
            type="submit"
            className="w-full py-2 text-xs font-semibold text-white bg-[var(--primary)] rounded-[var(--radius-md)] hover:brightness-110 active:brightness-95 transition-all shadow-sm cursor-pointer"
          >
            Submit Juror Ballot
          </button>
        </form>
      )}

      {/* Deliberation Floor */}
      {isDeliberationPrompt && (
        <form onSubmit={handleDeliberateSubmit} className="space-y-3">
          <div>
            <h5 className="font-bold text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">
              Jury Room Deliberation Discussion
            </h5>
            <p className="text-xs text-[var(--text-secondary)]">
              Share your perspective or challenge fellow jurors on reasonable doubt.
            </p>
          </div>

          <textarea
            rows={2}
            value={deliberationStatement}
            onChange={(e) => setDeliberationStatement(e.target.value)}
            placeholder="Speak to your fellow jurors..."
            className="w-full px-3 py-1.5 text-xs bg-[var(--background)] border border-[var(--border)] rounded-[var(--radius-sm)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] resize-none"
          />

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={handlePassDeliberation}
              className="px-3 py-1.5 text-xs border border-[var(--border)] rounded-[var(--radius-md)] hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer"
            >
              Pass Floor
            </button>
            <button
              type="submit"
              disabled={!deliberationStatement.trim()}
              className="px-4 py-1.5 text-xs font-semibold text-white bg-[var(--primary)] rounded-[var(--radius-md)] hover:brightness-110 disabled:opacity-50 cursor-pointer"
            >
              Address Jurors
            </button>
          </div>
        </form>
      )}

      {!isVotePrompt && !isDeliberationPrompt && (
        <div className="p-3 text-xs text-[var(--text-secondary)] bg-black/5 dark:bg-white/5 rounded text-center">
          Courtroom proceedings are underway. You will participate actively during jury deliberation rounds and ballot casting.
        </div>
      )}
    </div>
  );
}


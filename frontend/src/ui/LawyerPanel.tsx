import { useState, useEffect } from "react";
import { cn } from "../lib/utils";
import { useTrialStore } from "../store/trialStore";
import { trialWs } from "../events/trialWs";

interface LawyerPanelProps {
  className?: string;
}

const OBJECTION_TYPES = [
  { value: "hearsay", label: "Hearsay (BSA Sec. 21)" },
  { value: "leading", label: "Leading Question (BSA Sec. 146)" },
  { value: "relevance", label: "Relevance / Immaterial (BSA Sec. 3)" },
  { value: "badgering", label: "Badgering / Harassment" },
  { value: "speculation", label: "Calls for Speculation" },
];

export function LawyerPanel({ className }: LawyerPanelProps) {
  const mode = useTrialStore((state) => state.mode);
  const isHumanTurn = useTrialStore((state) => state.isHumanTurn);
  const setIsHumanTurn = useTrialStore((state) => state.setIsHumanTurn);
  const pendingPrompt = useTrialStore((state) => state.pendingPrompt);
  const objectionQuota = useTrialStore((state) => state.objectionQuota);
  const decrementObjectionQuota = useTrialStore(
    (state) => state.decrementObjectionQuota,
  );

  const [questionText, setQuestionText] = useState("");
  const [targetWitness, setTargetWitness] = useState("");
  const [selectedObjection, setSelectedObjection] = useState("hearsay");
  const [objectionReason, setObjectionReason] = useState("");
  const [showObjectionDialog, setShowObjectionDialog] = useState(false);

  // Keyboard shortcut: Press 'o' or 'O' to open objection window when enabled
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input or textarea
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return;
      }

      if ((e.key === "o" || e.key === "O") && objectionQuota > 0) {
        e.preventDefault();
        setShowObjectionDialog((prev) => !prev);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [objectionQuota]);

  // If not in lawyer mode, don't show the lawyer panel
  if (mode !== "lawyer") {
    return null;
  }

  const handleExamine = (e: React.FormEvent) => {
    e.preventDefault();
    if (!questionText.trim()) return;

    trialWs.sendHumanAction("examine", questionText.trim(), targetWitness || undefined);
    setQuestionText("");
    setIsHumanTurn(false);
  };

  const handleArgue = (e: React.FormEvent) => {
    e.preventDefault();
    if (!questionText.trim()) return;

    trialWs.sendHumanAction("argue", questionText.trim(), undefined);
    setQuestionText("");
    setIsHumanTurn(false);
  };

  const handlePass = () => {
    trialWs.sendHumanAction("pass", undefined, undefined);
    setIsHumanTurn(false);
  };

  const handleRaiseObjection = () => {
    if (objectionQuota <= 0) return;

    trialWs.sendObjection(selectedObjection, objectionReason.trim() || undefined);
    decrementObjectionQuota();
    setShowObjectionDialog(false);
    setObjectionReason("");
  };

  return (
    <div
      data-testid="lawyer-panel"
      className={cn(
        "bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] p-4 shadow-md space-y-4",
        className,
      )}
    >
      {/* Header with turn indicator and objection quota */}
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div className="flex items-center gap-2">
          <span
            data-testid="turn-indicator"
            className={cn(
              "w-2.5 h-2.5 rounded-full",
              isHumanTurn
                ? "bg-[var(--success)] animate-pulse"
                : "bg-neutral-400",
            )}
          />
          <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-primary)]">
            {isHumanTurn ? "Your Turn to Examine / Argue" : "Awaiting Floor..."}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <span
            data-testid="quota-display"
            className="text-xs text-[var(--text-secondary)] font-mono"
          >
            Objections remaining:{" "}
            <span
              className={cn(
                "font-bold",
                objectionQuota > 0 ? "text-[var(--primary)]" : "text-[var(--destructive)]",
              )}
            >
              {objectionQuota}/3
            </span>
          </span>

          <button
            type="button"
            data-testid="objection-button"
            aria-label="Raise Objection"
            title={
              objectionQuota <= 0
                ? "Objection quota exhausted (0 remaining)"
                : "Raise Objection (Press 'O')"
            }
            disabled={objectionQuota <= 0}
            onClick={() => setShowObjectionDialog((prev) => !prev)}
            className={cn(
              "px-3 py-1.5 text-xs font-bold uppercase tracking-wider rounded-[var(--radius-md)] border transition-all cursor-pointer",
              objectionQuota > 0
                ? "bg-[var(--destructive)] text-white hover:brightness-110 active:brightness-95 border-transparent shadow-sm"
                : "bg-neutral-200 dark:bg-neutral-800 text-neutral-400 border-[var(--border)] cursor-not-allowed opacity-60",
            )}
          >
            Objection! <span className="opacity-75 font-normal text-[10px] ml-1">(O)</span>
          </button>
        </div>
      </div>

      {/* Objection Popover Window */}
      {showObjectionDialog && (
        <div
          data-testid="objection-window"
          className="p-4 bg-red-50 dark:bg-red-950/30 border border-[var(--destructive)]/40 rounded-[var(--radius-md)] space-y-3 animate-in fade-in zoom-in-95 duration-150"
        >
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--destructive)]">
              Formal Legal Objection
            </h4>
            <button
              onClick={() => setShowObjectionDialog(false)}
              className="text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            >
              ✕
            </button>
          </div>

          <div className="space-y-2">
            <div>
              <label
                htmlFor="objection-type"
                className="block text-xs font-medium text-[var(--text-secondary)] mb-1"
              >
                Ground / Statutory Basis:
              </label>
              <select
                id="objection-type"
                value={selectedObjection}
                onChange={(e) => setSelectedObjection(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs bg-[var(--background)] border border-[var(--border)] rounded text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--destructive)]"
              >
                {OBJECTION_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="objection-reason"
                className="block text-xs font-medium text-[var(--text-secondary)] mb-1"
              >
                Reasoning / Basis (Optional):
              </label>
              <input
                id="objection-reason"
                type="text"
                placeholder="e.g. Question assumes facts not in evidence..."
                value={objectionReason}
                onChange={(e) => setObjectionReason(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs bg-[var(--background)] border border-[var(--border)] rounded text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--destructive)]"
              />
            </div>

            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => setShowObjectionDialog(false)}
                className="px-3 py-1 text-xs border border-[var(--border)] rounded hover:bg-neutral-100 dark:hover:bg-neutral-800"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleRaiseObjection}
                className="px-3 py-1 text-xs font-semibold text-white bg-[var(--destructive)] rounded hover:brightness-110 active:brightness-95"
              >
                Lodge Objection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Turn Action Form */}
      <div className={cn("space-y-3", !isHumanTurn && "opacity-50 pointer-events-none")}>
        {pendingPrompt?.options && pendingPrompt.options.length > 0 && (
          <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
            <span>Available Actions:</span>
            <div className="flex gap-1.5">
              {pendingPrompt.options.map((opt) => (
                <span
                  key={opt}
                  className="px-2 py-0.5 bg-[var(--primary)]/10 text-[var(--primary)] rounded font-mono text-[11px]"
                >
                  {opt}
                </span>
              ))}
            </div>
          </div>
        )}

        <div>
          <label
            htmlFor="lawyer-input"
            className="block text-xs font-medium text-[var(--text-secondary)] mb-1"
          >
            Question or Argument to the Court:
          </label>
          <textarea
            id="lawyer-input"
            rows={2}
            value={questionText}
            onChange={(e) => setQuestionText(e.target.value)}
            disabled={!isHumanTurn}
            placeholder={
              isHumanTurn
                ? "Type your question for the witness or argument for the court..."
                : "Waiting for other participants to conclude..."
            }
            className="w-full px-3 py-2 text-sm bg-[var(--background)] border border-[var(--border)] rounded-[var(--radius-sm)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)] resize-none"
          />
        </div>

        <div className="flex items-center justify-between gap-2">
          <input
            type="text"
            placeholder="Target Witness (e.g. Ramesh)"
            value={targetWitness}
            onChange={(e) => setTargetWitness(e.target.value)}
            disabled={!isHumanTurn}
            className="w-48 px-2.5 py-1 text-xs bg-[var(--background)] border border-[var(--border)] rounded text-[var(--text-primary)] focus:outline-none"
          />

          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={!isHumanTurn}
              onClick={handlePass}
              className="px-3 py-1.5 text-xs border border-[var(--border)] rounded-[var(--radius-md)] hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
            >
              Pass Floor
            </button>
            <button
              type="button"
              disabled={!isHumanTurn || !questionText.trim()}
              onClick={handleArgue}
              className="px-3 py-1.5 text-xs font-medium border border-[var(--primary)] text-[var(--primary)] rounded-[var(--radius-md)] hover:bg-[var(--primary)]/10 transition-colors cursor-pointer"
            >
              Argue / Submit
            </button>
            <button
              type="button"
              disabled={!isHumanTurn || !questionText.trim()}
              onClick={handleExamine}
              className="px-4 py-1.5 text-xs font-semibold text-white bg-[var(--primary)] rounded-[var(--radius-md)] hover:brightness-110 active:brightness-95 transition-all shadow-sm cursor-pointer"
            >
              Examine Witness
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}


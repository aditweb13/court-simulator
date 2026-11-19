import { cn } from "../lib/utils";
import { useTrialStore } from "../store/trialStore";
import { trialWs } from "../events/trialWs";

interface CaptionsProps {
  className?: string;
}

export function Captions({ className }: CaptionsProps) {
  const currentLine = useTrialStore((state) => state.currentLine);
  const acknowledgeCurrentLine = useTrialStore(
    (state) => state.acknowledgeCurrentLine,
  );

  if (!currentLine) {
    return null;
  }

  const roleStyles: Record<string, { badge: string; label: string }> = {
    judge: {
      badge: "bg-amber-500/20 text-amber-300 border-amber-500/40",
      label: "Hon. Judge Rao",
    },
    clerk: {
      badge: "bg-sky-500/20 text-sky-300 border-sky-500/40",
      label: "Court Clerk",
    },
    prosecutor: {
      badge: "bg-rose-500/20 text-rose-300 border-rose-500/40",
      label: "Public Prosecutor",
    },
    prosecution: {
      badge: "bg-rose-500/20 text-rose-300 border-rose-500/40",
      label: "Public Prosecutor",
    },
    defense: {
      badge: "bg-indigo-500/20 text-indigo-300 border-indigo-500/40",
      label: "Defense Counsel",
    },
    defendant: {
      badge: "bg-stone-500/20 text-stone-300 border-stone-500/40",
      label: "The Accused",
    },
    witness: {
      badge: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
      label: "Witness",
    },
    juror: {
      badge: "bg-purple-500/20 text-purple-300 border-purple-500/40",
      label: "Juror",
    },
  };

  const speakerKey = currentLine.speaker.toLowerCase();
  const meta = roleStyles[speakerKey] || {
    badge: "bg-neutral-500/20 text-neutral-300 border-neutral-500/40",
    label: currentLine.speaker,
  };

  const handleManualAdvance = () => {
    acknowledgeCurrentLine((seq) => trialWs.sendAck(seq));
  };

  return (
    <div
      className={cn(
        "absolute bottom-4 left-4 right-4 md:left-8 md:right-8 z-20 pointer-events-auto",
        className,
      )}
    >
      <div
        role="region"
        aria-live="polite"
        aria-atomic="true"
        className="max-w-4xl mx-auto bg-neutral-950/90 text-neutral-100 backdrop-blur-md border border-neutral-800 rounded-[var(--radius-lg)] p-4 md:p-5 shadow-2xl transition-all"
      >
        <div className="flex items-center justify-between gap-4 mb-2">
          <div className="flex items-center gap-2.5">
            <span
              className={cn(
                "px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider rounded border",
                meta.badge,
              )}
            >
              {meta.label}
            </span>
            {currentLine.action && (
              <span className="text-xs italic text-neutral-400">
                [{currentLine.action}]
              </span>
            )}
          </div>

          <button
            onClick={handleManualAdvance}
            className="text-xs text-neutral-400 hover:text-white px-2 py-1 rounded border border-neutral-700 hover:border-neutral-500 transition-colors cursor-pointer"
            title="Advance dialogue turn immediately"
            aria-label="Advance dialogue turn"
          >
            Advance ⏭
          </button>
        </div>

        <p className="font-serif text-base md:text-lg text-neutral-100 leading-relaxed tracking-wide">
          &ldquo;{currentLine.text}&rdquo;
        </p>
      </div>
    </div>
  );
}

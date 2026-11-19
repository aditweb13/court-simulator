import { useEffect, useRef } from "react";
import { useTrialStore } from "../store/trialStore";
import { cn } from "../lib/utils";

interface TranscriptProps {
  className?: string;
}

export function Transcript({ className }: TranscriptProps) {
  const transcript = useTrialStore((state) => state.transcript);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof bottomRef.current?.scrollIntoView === "function") {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [transcript.length]);

  return (
    <div
      className={cn(
        "bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] flex flex-col h-full overflow-hidden shadow-sm",
        className,
      )}
    >
      <div className="border-b border-[var(--border)] px-4 py-3 flex items-center justify-between bg-black/5 dark:bg-white/5">
        <h3 className="font-serif font-semibold text-sm tracking-wide text-[var(--primary)]">
          Official Court Record
        </h3>
        <span className="text-xs text-[var(--text-secondary)]">
          {transcript.length} {transcript.length === 1 ? "entry" : "entries"}
        </span>
      </div>

      <div
        className="flex-1 p-4 overflow-y-auto space-y-3 font-sans text-sm"
        role="log"
        aria-label="Courtroom Dialogue Transcript"
        aria-live="polite"
      >
        {transcript.length === 0 ? (
          <div className="text-center py-12 text-[var(--text-secondary)] italic">
            Nothing said yet. The court will record all proceedings here.
          </div>
        ) : (
          transcript.map((item, index) => {
            if (item.type === "ruling") {
              return (
                <div
                  key={`ruling-${item.seq}-${index}`}
                  className="p-2.5 rounded-[var(--radius-sm)] bg-amber-500/10 border border-amber-500/30 text-xs"
                >
                  <span className="font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wider">
                    Judicial Ruling:
                  </span>{" "}
                  Objection to &ldquo;{item.objection_type}&rdquo; is{" "}
                  <strong className="uppercase">{item.ruling}</strong>.
                  {item.struck && (
                    <span className="block mt-1 text-rose-500 font-medium">
                      ⚠️ Previous testimony struck from the record.
                    </span>
                  )}
                  {item.reason && (
                    <p className="mt-1 italic text-[var(--text-secondary)]">
                      &ldquo;{item.reason}&rdquo;
                    </p>
                  )}
                </div>
              );
            }

            return (
              <div
                key={`line-${item.seq}-${index}`}
                className="space-y-1 border-b border-[var(--border)]/50 pb-2.5 last:border-0"
              >
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span className="font-semibold capitalize text-[var(--text-primary)]">
                    {item.speaker}
                  </span>
                  <span className="tabular-nums">Seq #{item.seq}</span>
                </div>
                <p className="text-sm text-[var(--text-primary)] leading-relaxed font-serif">
                  {item.text}
                </p>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

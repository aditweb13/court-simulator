import React, { useEffect, useState } from "react";
import { useTrialStore } from "../store/trialStore";

interface VerdictDetailData {
  trial_id: string;
  outcome: "guilty" | "not_guilty" | "hung";
  score: number;
  j: number;
  p: number;
  threshold: number;
  disagreement: number;
  matches_truth?: boolean | null;
  truth?: {
    culprit?: string;
    motive?: string;
    summary?: string;
  } | null;
  sentence?: {
    section?: string;
    offense?: string;
    minimum?: string;
    maximum?: string;
    recommended?: string;
  } | null;
  judge_votes?: Array<{
    agent_id: string;
    role: string;
    kind: string;
    guilty?: boolean | null;
    guilt_probability?: number | null;
    confidence?: number | null;
    reasoning: string;
  }>;
  juror_final_votes?: Array<{
    agent_id: string;
    role: string;
    kind: string;
    guilty?: boolean | null;
    guilt_probability?: number | null;
    confidence?: number | null;
    reasoning: string;
  }>;
}

export const VerdictScreen: React.FC = () => {
  const { verdict, trialId, reset } = useTrialStore();
  const [isOpen, setIsOpen] = useState(true);
  const [details, setDetails] = useState<VerdictDetailData | null>(null);
  const [activeTab, setActiveTab] = useState<"summary" | "judges" | "truth">("summary");

  useEffect(() => {
    if (!verdict) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsOpen(true);

    if (trialId) {
      // Fetch rich breakdown from /api/v1/trials/:id/verdict
      fetch(`/api/v1/trials/${trialId}/verdict`)
        .then((res) => (res.ok ? res.json() : null))
        .then((json) => {
          if (json && json.data) {
            setDetails(json.data);
          }
        })
        .catch(() => {
          // Fall back gracefully to WebSocket verdict event data
        });
    }
  }, [verdict, trialId]);

  if (!verdict || !isOpen) {
    if (!verdict) return null;
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-40 px-4 py-2 bg-courtroom-ink text-courtroom-parchment rounded shadow-lg border border-courtroom-brass hover:bg-courtroom-brass hover:text-courtroom-ink font-serif text-sm transition-colors"
      >
        View Final Verdict
      </button>
    );
  }

  const outcome = verdict.outcome;
  const score = details?.score ?? verdict.score;
  const threshold = details?.threshold ?? verdict.threshold;
  const disagreement = details?.disagreement ?? verdict.disagreement;
  const matchesTruth = details?.matches_truth ?? verdict.matches_truth;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Courtroom Verdict Summary"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
    >
      <div className="bg-courtroom-parchment text-courtroom-ink border border-courtroom-border rounded-lg shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden font-serif">
        {/* Header Banner */}
        <div className="px-6 py-5 border-b border-courtroom-border bg-courtroom-surface flex items-center justify-between">
          <div>
            <span className="text-xs tracking-widest uppercase text-courtroom-muted font-mono block">
              Official Judgment Record
            </span>
            <h2 className="text-xl md:text-2xl font-bold tracking-tight">
              Sessions Court Verdict Pronouncement
            </h2>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="text-courtroom-muted hover:text-courtroom-ink text-lg px-2 py-1 rounded"
            aria-label="Dismiss verdict dialog"
          >
            ✕
          </button>
        </div>

        {/* Outcome Display Banner */}
        <div className="p-6 border-b border-courtroom-border text-center bg-courtroom-parchment">
          <div className="inline-block mb-3">
            {outcome === "guilty" && (
              <span className="px-6 py-2 rounded-full text-base font-bold uppercase tracking-wider bg-destructive/15 text-destructive border border-destructive/40">
                Guilty as Charged
              </span>
            )}
            {outcome === "not_guilty" && (
              <span className="px-6 py-2 rounded-full text-base font-bold uppercase tracking-wider bg-success/15 text-success border border-success/40">
                Acquitted & Discharged
              </span>
            )}
            {outcome === "hung" && (
              <span className="px-6 py-2 rounded-full text-base font-bold uppercase tracking-wider bg-amber-500/15 text-amber-600 border border-amber-500/40">
                Hung Jury / Mistrial
              </span>
            )}
          </div>

          <p className="text-sm text-courtroom-muted italic max-w-lg mx-auto">
            {verdict.reasoning || "Verdict resolved by combined jury vote and judicial bench probability."}
          </p>

          {/* Aggregated Score Bar */}
          <div className="mt-5 max-w-md mx-auto">
            <div className="flex justify-between text-xs font-mono text-courtroom-muted mb-1">
              <span>Combined Guilt Score: {(score * 100).toFixed(1)}%</span>
              <span>Threshold: {(threshold * 100).toFixed(0)}%</span>
            </div>
            <div className="w-full h-3 bg-courtroom-surface rounded-full overflow-hidden border border-courtroom-border relative">
              <div
                className={`h-full transition-all duration-700 ${
                  outcome === "guilty"
                    ? "bg-destructive"
                    : outcome === "not_guilty"
                      ? "bg-success"
                      : "bg-amber-500"
                }`}
                style={{ width: `${Math.min(100, Math.max(0, score * 100))}%` }}
              />
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-courtroom-ink z-10"
                style={{ left: `${threshold * 100}%` }}
                title="Threshold"
              />
            </div>
            <div className="flex justify-between text-[11px] text-courtroom-muted mt-1 font-mono">
              <span>0.5 × Jury + 0.5 × Bench</span>
              <span>Disagreement |J - P|: {(disagreement * 100).toFixed(1)}%</span>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-courtroom-border bg-courtroom-surface text-xs font-sans font-medium">
          <button
            onClick={() => setActiveTab("summary")}
            className={`flex-1 py-2.5 text-center transition-colors border-b-2 ${
              activeTab === "summary"
                ? "border-courtroom-brass text-courtroom-ink font-semibold bg-courtroom-parchment"
                : "border-transparent text-courtroom-muted hover:text-courtroom-ink"
            }`}
          >
            Sentencing & Findings
          </button>
          <button
            onClick={() => setActiveTab("judges")}
            className={`flex-1 py-2.5 text-center transition-colors border-b-2 ${
              activeTab === "judges"
                ? "border-courtroom-brass text-courtroom-ink font-semibold bg-courtroom-parchment"
                : "border-transparent text-courtroom-muted hover:text-courtroom-ink"
            }`}
          >
            Judicial Opinions ({details?.judge_votes?.length ?? 3})
          </button>
          <button
            onClick={() => setActiveTab("truth")}
            className={`flex-1 py-2.5 text-center transition-colors border-b-2 ${
              activeTab === "truth"
                ? "border-courtroom-brass text-courtroom-ink font-semibold bg-courtroom-parchment"
                : "border-transparent text-courtroom-muted hover:text-courtroom-ink"
            }`}
          >
            Ground Truth Reveal
          </button>
        </div>

        {/* Tab Content Body */}
        <div className="p-6 overflow-y-auto flex-1 text-sm space-y-4">
          {activeTab === "summary" && (
            <div className="space-y-4 animate-fade-in">
              {outcome === "guilty" && details?.sentence && (
                <div className="p-4 rounded border border-destructive/20 bg-destructive/5 space-y-1.5">
                  <span className="text-xs font-mono font-bold uppercase tracking-wider text-destructive block">
                    Statutory Sentence under Bharatiya Nyaya Sanhita, 2023
                  </span>
                  <p className="font-semibold text-base">{details.sentence.recommended}</p>
                  <p className="text-xs text-courtroom-muted">
                    Statutory Range: {details.sentence.minimum} to {details.sentence.maximum} (
                    {details.sentence.section})
                  </p>
                </div>
              )}

              {outcome === "not_guilty" && (
                <div className="p-4 rounded border border-success/20 bg-success/5 space-y-1">
                  <span className="text-xs font-mono font-bold uppercase tracking-wider text-success block">
                    Judicial Order of Acquittal
                  </span>
                  <p className="text-sm">
                    The accused is discharged of all charges. The bail bond stands cancelled and surety discharged.
                  </p>
                </div>
              )}

              {/* Jury breakdown */}
              {details?.juror_final_votes && details.juror_final_votes.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-courtroom-muted">
                    Jury Final Deliberation Votes ({details.juror_final_votes.length} Jurors)
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                    {details.juror_final_votes.map((jv, i) => (
                      <div
                        key={i}
                        className="p-2.5 rounded border border-courtroom-border bg-courtroom-surface space-y-1"
                      >
                        <div className="flex justify-between items-center">
                          <span className="font-semibold">Juror #{i + 1}</span>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                              jv.guilty
                                ? "bg-destructive/15 text-destructive"
                                : "bg-success/15 text-success"
                            }`}
                          >
                            {jv.guilty ? "Guilty" : "Not Guilty"}
                          </span>
                        </div>
                        <p className="text-courtroom-muted line-clamp-2">{jv.reasoning}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "judges" && (
            <div className="space-y-3 animate-fade-in">
              {details?.judge_votes && details.judge_votes.length > 0 ? (
                details.judge_votes.map((jv, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded border border-courtroom-border bg-courtroom-surface space-y-2"
                  >
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-xs font-mono uppercase tracking-wide text-courtroom-brass">
                        {idx === 0
                          ? "Textualist Philosophy"
                          : idx === 1
                            ? "Precedent & Doctrine Philosophy"
                            : "Constitutional Fairness Philosophy"}
                      </span>
                      <span className="text-xs font-mono text-courtroom-muted">
                        Assessed Guilt: {((jv.guilt_probability ?? 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-sm italic leading-relaxed text-courtroom-ink">
                      "{jv.reasoning}"
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-courtroom-muted italic text-center py-4">
                  Three judicial opinions recorded: Textualist, Precedent, and Fairness.
                </p>
              )}
            </div>
          )}

          {activeTab === "truth" && (
            <div className="space-y-4 animate-fade-in">
              <div
                className={`p-4 rounded border ${
                  matchesTruth === true
                    ? "border-success/30 bg-success/10 text-success"
                    : matchesTruth === false
                      ? "border-destructive/30 bg-destructive/10 text-destructive"
                      : "border-amber-500/30 bg-amber-500/10 text-amber-700"
                }`}
              >
                <div className="font-bold text-sm flex items-center gap-2">
                  {matchesTruth === true && <span>✓ Truth Concordance</span>}
                  {matchesTruth === false && <span>✗ Divergence from Reality</span>}
                  {matchesTruth === null && <span>~ Inconclusive (Mistrial)</span>}
                </div>
                <p className="text-xs mt-1 text-courtroom-ink">
                  {matchesTruth === true
                    ? "The simulation's combined verdict successfully matched the objective factual reality."
                    : matchesTruth === false
                      ? "The trial resulted in an outcome contrary to objective reality, demonstrating burden-of-proof dynamics."
                      : "The court hung without reaching the threshold."}
                </p>
              </div>

              {details?.truth && (
                <div className="p-4 rounded border border-courtroom-border bg-courtroom-surface space-y-2 text-xs">
                  <span className="font-mono font-bold uppercase tracking-wider text-courtroom-muted block">
                    Hidden Objective Ground Truth
                  </span>
                  <div>
                    <span className="font-semibold text-courtroom-ink">True Culprit: </span>
                    <span>{details.truth.culprit || "Unidentified"}</span>
                  </div>
                  <div>
                    <span className="font-semibold text-courtroom-ink">Actual Motive: </span>
                    <span className="text-courtroom-muted">{details.truth.motive || "None specified"}</span>
                  </div>
                  {details.truth.summary && (
                    <div>
                      <span className="font-semibold text-courtroom-ink">Factual Summary: </span>
                      <p className="text-courtroom-muted mt-1 leading-relaxed">
                        {details.truth.summary}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-courtroom-border bg-courtroom-surface flex items-center justify-between">
          <span className="text-xs text-courtroom-muted">
            Indian Criminal Trial Simulation (Verdicts per BSA / BNS 2023)
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsOpen(false)}
              className="px-4 py-1.5 rounded border border-courtroom-border hover:bg-courtroom-parchment text-xs font-serif transition-colors"
            >
              Review Courtroom
            </button>
            <button
              onClick={() => {
                reset();
                window.location.reload();
              }}
              className="px-4 py-1.5 rounded bg-courtroom-ink text-courtroom-parchment hover:bg-courtroom-brass hover:text-courtroom-ink text-xs font-serif font-semibold transition-colors"
            >
              New Trial
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

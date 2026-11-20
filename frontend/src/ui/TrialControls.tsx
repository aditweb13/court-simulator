import { useState, useEffect } from "react";
import { cn } from "../lib/utils";
import { TrialMode, useTrialStore } from "../store/trialStore";
import { trialWs } from "../events/trialWs";
import { CaseSummary, createTrial, fetchCases, getGuestToken } from "../lib/api";

interface TrialControlsProps {
  className?: string;
}

export function TrialControls({ className }: TrialControlsProps) {
  const trialId = useTrialStore((state) => state.trialId);
  const trialState = useTrialStore((state) => state.trialState);
  const status = useTrialStore((state) => state.status);
  const error = useTrialStore((state) => state.error);
  const setStatus = useTrialStore((state) => state.setStatus);
  const setError = useTrialStore((state) => state.setError);
  const setStoreMode = useTrialStore((state) => state.setMode);

  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>("case_001");
  const [selectedMode, setSelectedMode] = useState<string>("spectator");
  const [humanRole, setHumanRole] = useState<string>("prosecutor");
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    let mounted = true;
    fetchCases()
      .then((data) => {
        if (mounted && data.length > 0) {
          setCases(data);
          setSelectedCaseId(data[0].id || data[0].slug);
        }
      })
      .catch((err) => {
        console.error("Failed to fetch cases:", err);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const handleStartTrial = async () => {
    setLoading(true);
    setError(null);
    setStatus("connecting");

    try {
      const token = await getGuestToken();
      const actualRole = selectedMode === "lawyer" ? humanRole : null;
      setStoreMode(selectedMode as TrialMode, actualRole);
      const trial = await createTrial(selectedCaseId, selectedMode, actualRole);
      trialWs.connect(trial.id, token);
    } catch (err) {
      console.error("Start trial error:", err);
      setError(err instanceof Error ? err.message : "Failed to start trial");
      setStatus("error");
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = () => {
    trialWs.disconnect();
  };

  const isRunning = status === "running" || status === "connecting";

  return (
    <div
      className={cn(
        "bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-sm space-y-4",
        className,
      )}
    >
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div>
          <h3 className="font-serif font-semibold text-base text-[var(--primary)]">
            Trial Control Panel
          </h3>
          <p className="text-xs text-[var(--text-secondary)]">
            Configure proceedings & simulate judicial simulation
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={cn(
              "w-2.5 h-2.5 rounded-full",
              status === "running"
                ? "bg-[var(--success)] animate-pulse"
                : status === "connecting"
                  ? "bg-amber-500 animate-ping"
                  : status === "error"
                    ? "bg-[var(--destructive)]"
                    : "bg-neutral-400",
            )}
          />
          <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-primary)]">
            {status === "running" ? `In Session (${trialState})` : status}
          </span>
        </div>
      </div>

      {error && (
        <div
          role="alert"
          className="p-3 bg-[var(--destructive)]/10 border border-[var(--destructive)]/30 rounded-[var(--radius-sm)] text-xs text-[var(--destructive)] flex items-center justify-between"
        >
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="text-[var(--text-secondary)] hover:text-[var(--destructive)] ml-2"
          >
            ✕
          </button>
        </div>
      )}

      {!isRunning ? (
        <div className="space-y-4">
          <div>
            <label
              htmlFor="case-select"
              className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5"
            >
              Select Court Docket / Case:
            </label>
            <select
              id="case-select"
              value={selectedCaseId}
              onChange={(e) => setSelectedCaseId(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-[var(--background)] border border-[var(--border)] rounded-[var(--radius-sm)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)] cursor-pointer"
            >
              {cases.length > 0 ? (
                cases.map((c) => (
                  <option key={c.id || c.slug} value={c.id || c.slug}>
                    {c.title} ({c.charge})
                  </option>
                ))
              ) : (
                <option value="case_001">
                  State of Maharashtra v. K. Sharma (BNS Sec. 103)
                </option>
              )}
            </select>
          </div>

          <div>
            <label
              htmlFor="mode-select"
              className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5"
            >
              Mode of Participation:
            </label>
            <select
              id="mode-select"
              value={selectedMode}
              onChange={(e) => setSelectedMode(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-[var(--background)] border border-[var(--border)] rounded-[var(--radius-sm)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)] cursor-pointer"
            >
              <option value="spectator">Spectator / Watch Simulation</option>
              <option value="lawyer">Human Lawyer Mode (Interactive)</option>
              <option value="judge">Play as Judge</option>
              <option value="juror">Play as Juror</option>
            </select>
          </div>

          {selectedMode === "lawyer" && (
            <div>
              <label
                htmlFor="role-select"
                className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5"
              >
                Counsel Role:
              </label>
              <select
                id="role-select"
                value={humanRole}
                onChange={(e) => setHumanRole(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-[var(--background)] border border-[var(--border)] rounded-[var(--radius-sm)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)] cursor-pointer"
              >
                <option value="prosecutor">Public Prosecutor</option>
                <option value="defense">Defense Counsel</option>
              </select>
            </div>
          )}

          <button
            onClick={handleStartTrial}
            disabled={loading}
            className={cn(
              "w-full h-10 px-5 text-sm font-semibold text-white bg-[var(--primary)] rounded-[var(--radius-md)] shadow hover:brightness-110 active:brightness-95 transition-all cursor-pointer",
              "focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:ring-offset-2",
              loading && "opacity-60 cursor-not-allowed",
            )}
          >
            {loading ? "Convening Court..." : "Start Trial Proceeding"}
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="p-3 bg-black/5 dark:bg-white/5 rounded-[var(--radius-sm)] space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-[var(--text-secondary)]">Trial Reference:</span>
              <span className="font-mono">{trialId?.slice(0, 8)}...</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--text-secondary)]">Current Phase:</span>
              <span className="font-semibold text-[var(--primary)]">{trialState}</span>
            </div>
          </div>

          <button
            onClick={handleDisconnect}
            className="w-full h-10 px-4 text-xs font-semibold text-[var(--destructive)] border border-[var(--destructive)]/40 hover:bg-[var(--destructive)]/10 rounded-[var(--radius-md)] transition-colors cursor-pointer"
          >
            Adjourn / End Session
          </button>
        </div>
      )}
    </div>
  );
}


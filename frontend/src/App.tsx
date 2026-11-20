import { useState, useEffect } from "react";
import { cn } from "./lib/utils";
import { CourtroomCanvas } from "./scene/CourtroomCanvas";
import { TrialControls } from "./ui/TrialControls";
import { Transcript } from "./ui/Transcript";
import { VerdictScreen } from "./ui/VerdictScreen";
import { AdminPage } from "./ui/AdminPage";
import { LawyerPanel } from "./ui/LawyerPanel";
import { JudgePanel } from "./ui/JudgePanel";
import { JurorPanel } from "./ui/JurorPanel";
import { ReplayControls } from "./ui/ReplayControls";
import { DisclaimerModal } from "./ui/DisclaimerModal";
import { useTrialStore } from "./store/trialStore";

export default function App() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("verdict_theme");
      if (stored === "dark" || stored === "light") return stored;
    }
    return "light";
  });
  const [route, setRoute] = useState<string>(
    typeof window !== "undefined" && window.location.pathname.startsWith("/admin")
      ? "/admin"
      : "/",
  );
  const trialState = useTrialStore((state) => state.trialState);
  const status = useTrialStore((state) => state.status);
  const ttsEnabled = useTrialStore((state) => state.ttsEnabled);
  const setTTSEnabled = useTrialStore((state) => state.setTTSEnabled);
  const sfxEnabled = useTrialStore((state) => state.sfxEnabled);
  const setSFXEnabled = useTrialStore((state) => state.setSFXEnabled);
  const [showReplay, setShowReplay] = useState<boolean>(false);
  const [showDisclaimer, setShowDisclaimer] = useState<boolean>(false);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    const onPopState = () => {
      setRoute(window.location.pathname.startsWith("/admin") ? "/admin" : "/");
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigate = (to: string) => {
    window.history.pushState({}, "", to);
    setRoute(to);
  };

  const toggleTheme = () => {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    if (typeof window !== "undefined") {
      localStorage.setItem("verdict_theme", next);
    }
    document.documentElement.setAttribute("data-theme", next);
  };

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--text-primary)] transition-colors flex flex-col font-sans">
      {/* Accessible skip link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-[var(--primary)] focus:text-white focus:rounded focus:ring-2 focus:ring-[var(--focus)]"
      >
        Skip to courtroom proceedings
      </a>

      {/* Primary Application Header */}
      <header className="border-b border-[var(--border)] px-6 py-4 flex items-center justify-between bg-[var(--surface)] shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-[var(--primary)] text-white flex items-center justify-center font-serif font-bold text-lg shadow-sm">
            ⚖
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl md:text-2xl font-serif font-bold tracking-tight text-[var(--primary)]">
                Verdict
              </h1>
              <span className="text-[11px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded bg-black/5 dark:bg-white/10 text-[var(--text-secondary)] border border-[var(--border)]">
                BNS 2023 Edition
              </span>
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              Indian Courtroom Trial Simulator & Autonomous Multi-Agent Justice System
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 text-xs text-[var(--text-secondary)] border-r border-[var(--border)] pr-4">
            <span>State:</span>
            <span className="font-semibold text-[var(--primary)] uppercase">
              {status === "running" ? trialState : status}
            </span>
          </div>

          <button
            onClick={() => setTTSEnabled(!ttsEnabled)}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded-[var(--radius-md)] border transition-colors cursor-pointer",
              ttsEnabled
                ? "bg-[var(--primary)] text-white border-transparent"
                : "border-[var(--border)] hover:bg-black/5 dark:hover:bg-white/5",
            )}
            aria-label={ttsEnabled ? "Mute text-to-speech audio" : "Enable text-to-speech audio"}
            title="Toggle Text-to-Speech Courtroom Dialogue"
          >
            {ttsEnabled ? "🔊 Voice: ON" : "🔈 Voice: OFF"}
          </button>

          <button
            onClick={() => setSFXEnabled(!sfxEnabled)}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded-[var(--radius-md)] border transition-colors cursor-pointer",
              sfxEnabled
                ? "bg-[var(--primary)] text-white border-transparent"
                : "border-[var(--border)] hover:bg-black/5 dark:hover:bg-white/5",
            )}
            aria-label={sfxEnabled ? "Mute sound effects" : "Enable sound effects"}
            title="Toggle Gavel & Courtroom Sound Effects"
          >
            {sfxEnabled ? "🔔 SFX: ON" : "🔕 SFX: OFF"}
          </button>

          <button
            onClick={() => setShowReplay((prev) => !prev)}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded-[var(--radius-md)] border transition-colors cursor-pointer",
              showReplay
                ? "bg-amber-600 text-white border-transparent"
                : "border-[var(--border)] hover:bg-black/5 dark:hover:bg-white/5",
            )}
            aria-label="Toggle trial replay controls"
          >
            📹 Replay
          </button>

          <button
            onClick={() => navigate(route === "/admin" ? "/" : "/admin")}
            className={cn(
              "px-3.5 py-1.5 text-xs font-medium rounded-[var(--radius-md)] border border-[var(--border)]",
              "hover:border-[var(--primary)] hover:bg-black/5 dark:hover:bg-white/5 transition-colors cursor-pointer",
            )}
            aria-label={route === "/admin" ? "Return to Courtroom" : "Open Admin Gateway"}
          >
            {route === "/admin" ? "⚖ Courtroom" : "⚙ Admin"}
          </button>

          <button
            onClick={toggleTheme}
            className={cn(
              "px-3.5 py-1.5 text-xs font-medium rounded-[var(--radius-md)] border border-[var(--border)]",
              "hover:border-[var(--primary)] hover:bg-black/5 dark:hover:bg-white/5 transition-colors cursor-pointer",
            )}
            aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
          >
            {theme === "light" ? "🌙 Dark Mode" : "☀️ Light Mode"}
          </button>
        </div>
      </header>

      {/* Conditional rendering for /admin vs main courtroom */}
      {route === "/admin" ? (
        <AdminPage onBack={() => navigate("/")} />
      ) : (
        /* Main Courtroom Simulation Interface */
        <main
          id="main-content"
          className="flex-1 max-w-[1360px] w-full mx-auto p-4 md:p-6 flex flex-col gap-6"
        >
          {/* 3D Viewport Chamber Shell */}
        <section
          className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] overflow-hidden shadow-sm flex flex-col"
          aria-label="3D Courtroom Simulation Chamber"
        >
          <div className="border-b border-[var(--border)] px-4 py-2.5 flex items-center justify-between bg-black/5 dark:bg-white/5 text-xs">
            <div className="flex items-center gap-2">
              <span className="font-serif font-semibold text-sm tracking-wide text-[var(--primary)]">
                Courtroom Chambers — Live View
              </span>
              <span className="text-[10px] text-[var(--text-secondary)]">
                • Sessions Court of Greater Mumbai
              </span>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-[var(--success)]/10 text-[var(--success)] font-medium text-[11px] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--success)] animate-pulse" />
              Engine Online
            </span>
          </div>

          <div className="h-[480px] md:h-[540px] w-full relative bg-neutral-950">
            <CourtroomCanvas />
          </div>
        </section>

        {/* Proceedings Grid: Controls + Official Record */}
        <section
          className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[420px]"
          aria-label="Courtroom Controls and Transcript"
        >
          {/* Left Column: Trial Controls & Case Docket */}
          <div className="lg:col-span-4 flex flex-col gap-4">
            {showReplay && <ReplayControls onClose={() => setShowReplay(false)} />}
            <TrialControls />

            <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] p-4 text-xs space-y-2 text-[var(--text-secondary)]">
              <h4 className="font-serif font-semibold text-sm text-[var(--primary)]">
                Courtroom Protocol
              </h4>
              <p>
                Proceedings follow the Bharatiya Nagarik Suraksha Sanhita (BNSS),
                2023 and the Bharatiya Sakshya Adhiniyam (BSA), 2023.
              </p>
              <div className="pt-2 border-t border-[var(--border)] flex justify-between text-[11px]">
                <span>Coram: Sole Judicial Magistrate</span>
                <span>Jury Panel: 7 Citizen Assessors</span>
              </div>
            </div>
          </div>

          {/* Right Column: Official Transcript Stream & Interactive Panels */}
          <div className="lg:col-span-8 flex flex-col gap-4">
            <Transcript className="h-[460px]" />
            <LawyerPanel />
            <JudgePanel />
            <JurorPanel />
          </div>
        </section>
      </main>
      )}

      {/* Educational Legal Disclaimer Footer */}
      <footer className="border-t border-[var(--border)] px-6 py-3 bg-[var(--surface)] text-[11px] text-[var(--text-secondary)] flex flex-col sm:flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span>
            ⚖ Verdict BNS Simulator is an autonomous multi-agent courtroom research system for educational evaluation under BNS, BNSS & BSA 2023. Not legal advice.
          </span>
          <button
            onClick={() => setShowDisclaimer(true)}
            className="underline font-semibold text-[var(--primary)] hover:brightness-110 cursor-pointer ml-1"
          >
            Legal Notice & Ethics Charter
          </button>
        </div>
        <div className="flex gap-4">
          <span>Coram: Sessions Court</span>
          <span>Version: 1.0 (BNS 2023 Edition)</span>
        </div>
      </footer>

      <VerdictScreen />
      <DisclaimerModal isOpen={showDisclaimer} onClose={() => setShowDisclaimer(false)} />
    </div>
  );
}

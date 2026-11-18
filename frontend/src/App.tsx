import { useState } from "react";
import { cn } from "./lib/utils";
import { CourtroomCanvas } from "./scene/CourtroomCanvas";

export default function App() {
  const [theme, setTheme] = useState<"light" | "dark">("light");

  const toggleTheme = () => {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
  };

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--text-primary)] transition-colors flex flex-col">
      <header className="border-b border-[var(--border)] px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-serif font-semibold text-[var(--primary)]">
            Verdict
          </h1>
          <p className="text-sm text-[var(--text-secondary)]">
            3D Courtroom Simulator & Multi-Agent Justice System
          </p>
        </div>
        <button
          onClick={toggleTheme}
          className={cn(
            "px-4 py-2 text-sm font-medium rounded-[var(--radius-md)] border border-[var(--border)]",
            "hover:border-[var(--primary)] transition-colors cursor-pointer",
          )}
        >
          Theme: {theme === "light" ? "Light" : "Dark"}
        </button>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 flex flex-col gap-6">
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] overflow-hidden shadow-sm flex flex-col">
          <div className="border-b border-[var(--border)] px-6 py-3 flex items-center justify-between bg-black/5 dark:bg-white/5">
            <span className="font-serif font-semibold text-sm tracking-wide text-[var(--primary)]">
              Courtroom Chambers — Live View
            </span>
            <span className="text-xs px-2.5 py-1 rounded-full bg-[var(--success)]/10 text-[var(--success)] font-medium">
              3D Engine Ready
            </span>
          </div>

          <div className="h-[480px] w-full relative bg-neutral-950">
            <CourtroomCanvas />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5">
            <h3 className="font-serif font-semibold text-lg text-[var(--primary)] mb-1">
              Case Docket
            </h3>
            <p className="text-sm text-[var(--text-secondary)]">
              State of Maharashtra v. K. Sharma (BNS Sec. 103)
            </p>
          </div>

          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5">
            <h3 className="font-serif font-semibold text-lg text-[var(--secondary)] mb-1">
              Court Officials
            </h3>
            <p className="text-sm text-[var(--text-secondary)]">
              Hon. Judge Rao, Special Prosecutor, Public Defense Counsel
            </p>
          </div>

          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5">
            <h3 className="font-serif font-semibold text-lg text-[var(--text-primary)] mb-1">
              Jury Status
            </h3>
            <p className="text-sm text-[var(--text-secondary)]">
              7 Juror Agents Seated • Awaiting Examination
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

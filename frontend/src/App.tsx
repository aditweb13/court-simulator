import { useState } from "react";
import { cn } from "./lib/utils";

export default function App() {
  const [theme, setTheme] = useState<"light" | "dark">("light");

  const toggleTheme = () => {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
  };

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--text-primary)] transition-colors">
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
            "hover:border-[var(--primary)] transition-colors",
          )}
        >
          Theme: {theme === "light" ? "Light" : "Dark"}
        </button>
      </header>

      <main className="max-w-6xl mx-auto p-6 space-y-6">
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] p-6 shadow-sm">
          <h2 className="text-xl font-serif font-semibold mb-2 text-[var(--primary)]">
            Court In Session
          </h2>
          <p className="text-[var(--text-secondary)]">
            Indian Criminal Law Simulator powered by isolated LLM agents and hybrid statutory retrieval.
          </p>
        </div>
      </main>
    </div>
  );
}


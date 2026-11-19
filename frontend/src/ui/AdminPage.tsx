import React, { useEffect, useState, useCallback } from "react";
import { fetchLLMStatus, ProviderStatus } from "../lib/api";
import { cn } from "../lib/utils";

export interface AdminPageProps {
  onBack?: () => void;
  token?: string;
}

export function AdminPage({ onBack, token: initialToken }: AdminPageProps) {
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [adminToken, setAdminToken] = useState<string>(
    initialToken || sessionStorage.getItem("verdict_token") || "",
  );
  const [tokenInput, setTokenInput] = useState<string>("");
  const [showTokenPrompt, setShowTokenPrompt] = useState<boolean>(false);

  useEffect(() => {
    let active = true;
    fetchLLMStatus(adminToken || undefined)
      .then((data) => {
        if (active) {
          setProviders(data);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          const message = err instanceof Error ? err.message : "Failed to load LLM status";
          setError(message);
          if (message.toLowerCase().includes("admin") || message.toLowerCase().includes("403")) {
            setShowTokenPrompt(true);
          }
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [adminToken]);

  const handleRefresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchLLMStatus(adminToken || undefined);
      setProviders(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load LLM status";
      setError(message);
      if (message.toLowerCase().includes("admin") || message.toLowerCase().includes("403")) {
        setShowTokenPrompt(true);
      }
    } finally {
      setLoading(false);
    }
  }, [adminToken]);

  const handleSaveToken = (e: React.FormEvent) => {
    e.preventDefault();
    if (!tokenInput.trim()) return;
    const cleanToken = tokenInput.trim();
    setAdminToken(cleanToken);
    sessionStorage.setItem("verdict_token", cleanToken);
    setShowTokenPrompt(false);
  };

  // Compute summary stats
  const totalKeys = providers.reduce((acc, p) => acc + p.total_keys, 0);
  const readyKeys = providers.reduce((acc, p) => acc + p.ready_keys, 0);
  const coolingKeys = providers.reduce((acc, p) => acc + p.cooling_keys, 0);
  const totalCalls = providers.reduce(
    (acc, p) => acc + p.keys.reduce((kAcc, k) => kAcc + k.recent_call_count, 0),
    0,
  );

  return (
    <div
      className="min-h-screen bg-[var(--background)] text-[var(--text-primary)] p-4 md:p-8 flex flex-col font-sans"
      data-testid="admin-page"
    >
      <div className="max-w-6xl w-full mx-auto flex flex-col gap-6">
        {/* Navigation & Header */}
        <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--border)] pb-4">
          <div className="flex items-center gap-3">
            {onBack && (
              <button
                type="button"
                onClick={onBack}
                className={cn(
                  "px-3 py-1.5 text-xs font-medium rounded-[var(--radius-md)] border border-[var(--border)]",
                  "hover:border-[var(--primary)] hover:bg-black/5 dark:hover:bg-white/5 transition-colors cursor-pointer",
                )}
                aria-label="Back to Courtroom"
              >
                ← Back
              </button>
            )}
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl md:text-2xl font-serif font-bold text-[var(--primary)]">
                  System Administration
                </h1>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-[var(--primary)] text-white">
                  LLM Gateway
                </span>
              </div>
              <p className="text-xs text-[var(--text-secondary)]">
                Real-time multi-provider pool observability, key cooldowns, and audit metrics
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowTokenPrompt(!showTokenPrompt)}
              className={cn(
                "px-3 py-1.5 text-xs font-medium rounded-[var(--radius-md)] border border-[var(--border)]",
                "hover:border-[var(--primary)] transition-colors cursor-pointer text-[var(--text-secondary)]",
              )}
            >
              🔑 {adminToken ? "Update Token" : "Provide Admin Token"}
            </button>
            <button
              type="button"
              onClick={handleRefresh}
              disabled={loading}
              className={cn(
                "px-4 py-1.5 text-xs font-medium rounded-[var(--radius-md)] bg-[var(--primary)] text-white",
                "hover:opacity-90 disabled:opacity-50 transition-all cursor-pointer flex items-center gap-1.5",
              )}
              aria-label="Refresh Status"
            >
              🔄 Refresh Status
            </button>
          </div>
        </header>

        {/* Optional Admin Token Configuration Drawer */}
        {showTokenPrompt && (
          <form
            onSubmit={handleSaveToken}
            className="p-4 bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] shadow-xs flex flex-col sm:flex-row gap-3 items-end"
            aria-label="Admin token configuration"
          >
            <div className="flex-1 w-full space-y-1">
              <label
                htmlFor="admin-token-input"
                className="text-xs font-medium text-[var(--text-primary)]"
              >
                Admin Bearer Token
              </label>
              <input
                id="admin-token-input"
                type="password"
                placeholder="Paste JWT token associated with an ADMIN_EMAILS user..."
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                className="w-full text-xs px-3 py-2 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-medium rounded-[var(--radius-md)] bg-[var(--primary)] text-white hover:opacity-90 transition-opacity"
            >
              Save Token
            </button>
          </form>
        )}

        {/* State 1: Loading State (Table Skeleton) */}
        {loading && (
          <div
            className="space-y-4"
            aria-busy="true"
            aria-label="Loading LLM pool status"
            data-testid="admin-loading"
          >
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="h-20 bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] animate-pulse"
                />
              ))}
            </div>

            <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] p-4 space-y-3">
              <div className="h-6 w-48 bg-black/10 dark:bg-white/10 rounded animate-pulse" />
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className="h-10 bg-black/5 dark:bg-white/5 rounded animate-pulse"
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* State 2: Error State (Message plus Retry button per Design.md) */}
        {!loading && error && (
          <div
            className="p-6 bg-[var(--surface)] border border-[var(--destructive)]/40 rounded-[var(--radius-lg)] flex flex-col items-center justify-center text-center gap-3"
            role="alert"
            data-testid="admin-error"
          >
            <div className="w-10 h-10 rounded-full bg-[var(--destructive)]/10 text-[var(--destructive)] flex items-center justify-center text-lg font-bold">
              ⚠
            </div>
            <h2 className="text-base font-serif font-semibold text-[var(--destructive)]">
              Access Restricted or Service Unavailable
            </h2>
            <p className="text-xs text-[var(--text-secondary)] max-w-md">{error}</p>
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={handleRefresh}
                className="px-4 py-2 text-xs font-medium rounded-[var(--radius-md)] bg-[var(--primary)] text-white hover:opacity-90 transition-opacity cursor-pointer"
              >
                Retry
              </button>
              <button
                type="button"
                onClick={() => setShowTokenPrompt(true)}
                className="px-4 py-2 text-xs font-medium rounded-[var(--radius-md)] border border-[var(--border)] hover:bg-black/5 dark:hover:bg-white/5 transition-colors cursor-pointer"
              >
                Provide Token
              </button>
            </div>
          </div>
        )}

        {/* State 3: Empty State ("No LLM calls yet" per Design.md) */}
        {!loading && !error && totalCalls === 0 && (
          <div
            className="p-8 bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] flex flex-col items-center justify-center text-center gap-3"
            data-testid="admin-empty"
          >
            <div className="text-3xl text-[var(--text-secondary)]">📊</div>
            <h2 className="text-base font-serif font-semibold text-[var(--primary)]">
              No LLM calls yet
            </h2>
            <p className="text-xs text-[var(--text-secondary)] max-w-md">
              The LLM router is online and pools are configured, but no trial inferences or model calls
              have been recorded in the database audit log.
            </p>
          </div>
        )}

        {/* State 4: Data View */}
        {!loading && !error && (
          <div className="space-y-6" data-testid="admin-content">
            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] p-4">
                <span className="text-[11px] text-[var(--text-secondary)] uppercase tracking-wider">
                  Total Keys
                </span>
                <p className="text-2xl font-serif font-bold text-[var(--primary)] mt-1">
                  {totalKeys}
                </p>
                <span className="text-[10px] text-[var(--text-secondary)]">Across all providers</span>
              </div>

              <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] p-4">
                <span className="text-[11px] text-[var(--text-secondary)] uppercase tracking-wider">
                  Ready Keys
                </span>
                <p className="text-2xl font-serif font-bold text-[var(--success)] mt-1">
                  {readyKeys}
                </p>
                <span className="text-[10px] text-[var(--text-secondary)]">Available immediately</span>
              </div>

              <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] p-4">
                <span className="text-[11px] text-[var(--text-secondary)] uppercase tracking-wider">
                  Cooling Down
                </span>
                <p
                  className={cn(
                    "text-2xl font-serif font-bold mt-1",
                    coolingKeys > 0 ? "text-[var(--destructive)]" : "text-[var(--text-secondary)]",
                  )}
                >
                  {coolingKeys}
                </p>
                <span className="text-[10px] text-[var(--text-secondary)]">On backoff timer</span>
              </div>

              <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] p-4">
                <span className="text-[11px] text-[var(--text-secondary)] uppercase tracking-wider">
                  Recorded Inferences
                </span>
                <p className="text-2xl font-serif font-bold text-[var(--secondary)] mt-1">
                  {totalCalls}
                </p>
                <span className="text-[10px] text-[var(--text-secondary)]">Logged in database</span>
              </div>
            </div>

            {/* Provider Tables */}
            <div className="space-y-6">
              {providers.map((provider) => (
                <section
                  key={provider.provider}
                  className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] overflow-hidden shadow-xs"
                  aria-labelledby={`provider-heading-${provider.provider}`}
                >
                  <div className="border-b border-[var(--border)] px-4 py-3 bg-black/5 dark:bg-white/5 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <h2
                        id={`provider-heading-${provider.provider}`}
                        className="font-serif font-semibold text-sm capitalize text-[var(--primary)]"
                      >
                        {provider.provider} Pool
                      </h2>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-black/5 dark:bg-white/10 text-[var(--text-secondary)] font-mono">
                        {provider.total_keys} {provider.total_keys === 1 ? "key" : "keys"}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-[var(--success)] font-medium">
                        ● {provider.ready_keys} ready
                      </span>
                      {provider.cooling_keys > 0 && (
                        <span className="text-[var(--destructive)] font-medium">
                          ⚠ {provider.cooling_keys} cooling
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="border-b border-[var(--border)] bg-black/2 dark:bg-white/2 text-[var(--text-secondary)]">
                        <tr>
                          <th scope="col" className="px-4 py-2.5 font-medium">
                            Key Alias
                          </th>
                          <th scope="col" className="px-4 py-2.5 font-medium">
                            Status
                          </th>
                          <th scope="col" className="px-4 py-2.5 font-medium">
                            Fail Count
                          </th>
                          <th scope="col" className="px-4 py-2.5 font-medium">
                            Last Outcome
                          </th>
                          <th scope="col" className="px-4 py-2.5 font-medium">
                            Calls Logged
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border)]">
                        {provider.keys.length === 0 ? (
                          <tr>
                            <td
                              colSpan={5}
                              className="px-4 py-4 text-center text-[var(--text-secondary)] italic"
                            >
                              No keys configured for this provider.
                            </td>
                          </tr>
                        ) : (
                          provider.keys.map((k) => (
                            <tr
                              key={k.key_alias}
                              className="hover:bg-black/2 dark:hover:bg-white/2 transition-colors"
                            >
                              <td className="px-4 py-2.5 font-mono font-medium text-[var(--primary)]">
                                {k.key_alias}
                              </td>
                              <td className="px-4 py-2.5">
                                {k.is_ready ? (
                                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[var(--success)]/10 text-[var(--success)]">
                                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--success)]" />
                                    Ready
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[var(--destructive)]/10 text-[var(--destructive)]">
                                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--destructive)] animate-pulse" />
                                    Cooling ({k.cooling_down_seconds.toFixed(0)}s remaining)
                                  </span>
                                )}
                              </td>
                              <td className="px-4 py-2.5 text-[var(--text-secondary)]">
                                {k.fail_count}
                              </td>
                              <td className="px-4 py-2.5">
                                {k.last_status ? (
                                  <span
                                    className={cn(
                                      "px-1.5 py-0.5 rounded text-[10px] font-mono uppercase",
                                      k.last_status === "ok"
                                        ? "bg-[var(--success)]/10 text-[var(--success)]"
                                        : "bg-[var(--destructive)]/10 text-[var(--destructive)]",
                                    )}
                                  >
                                    {k.last_status}
                                  </span>
                                ) : (
                                  <span className="text-[var(--text-secondary)] italic">none</span>
                                )}
                              </td>
                              <td className="px-4 py-2.5 font-medium">{k.recent_call_count}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </section>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

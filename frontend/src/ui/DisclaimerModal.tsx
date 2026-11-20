import { useEffect, useRef } from "react";

interface DisclaimerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function DisclaimerModal({ isOpen, onClose }: DisclaimerModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (isOpen) {
      modalRef.current?.focus();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="disclaimer-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs"
    >
      <div
        ref={modalRef}
        tabIndex={-1}
        className="relative w-full max-w-2xl max-h-[85vh] overflow-y-auto bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-lg)] p-6 shadow-2xl space-y-5 focus:outline-none"
        data-testid="disclaimer-modal"
      >
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
          <div className="flex items-center gap-2">
            <span className="text-xl">⚖️</span>
            <h2 id="disclaimer-title" className="text-lg font-serif font-bold text-[var(--primary)]">
              Legal Notice, Ethics Charter & Simulator Scope
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer text-sm font-semibold"
            aria-label="Close legal notice"
          >
            ✕
          </button>
        </div>

        <div className="space-y-4 text-xs leading-relaxed text-[var(--text-primary)]">
          <section className="space-y-1.5 p-3 rounded-[var(--radius-sm)] bg-amber-500/10 border border-amber-500/20">
            <h3 className="font-semibold text-amber-700 dark:text-amber-400 uppercase tracking-wide text-[11px]">
              Educational & Research Simulation Notice
            </h3>
            <p>
              <strong>Verdict: BNS Edition</strong> is an autonomous multi-agent courtroom research system
              and educational simulator modeled upon the criminal procedural frameworks of the{" "}
              <strong>Bharatiya Nyaya Sanhita, 2023 (BNS)</strong>,{" "}
              <strong>Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)</strong>, and{" "}
              <strong>Bharatiya Sakshya Adhiniyam, 2023 (BSA)</strong>.
            </p>
            <p>
              This software is designed solely for algorithmic evaluation, legal technology research, and
              academic study. It does not provide legal advice, represent actual judicial proceedings, or
              substitute for the professional counsel of an Advocate enrolled under the Advocates Act, 1961.
            </p>
          </section>

          <section className="space-y-1.5">
            <h3 className="font-semibold text-[var(--primary)] text-sm">
              Ethical AI Charter & Demographic Neutrality
            </h3>
            <p>
              In strict adherence to the project&apos;s ethical charter, all synthetic juror personas are defined
              exclusively by cognitive reasoning styles (e.g. analytical, holistic, evidence-driven, doctrinal)
              and professional or civic backgrounds. Under no circumstances are protected demographic
              attributes—such as religion, caste, gender, ethnicity, community, or socioeconomic identity—used
              in juror prompts or deliberation biases.
            </p>
          </section>

          <section className="space-y-1.5">
            <h3 className="font-semibold text-[var(--primary)] text-sm">
              Section 52(1)(q) Indian Copyright Act Compliance
            </h3>
            <p>
              All statutory enactments, penal sections, procedural provisions, and legislative texts
              incorporated within this system are reproduced under Section 52(1)(q) of the Indian Copyright
              Act, 1957, which explicitly excludes from infringement the reproduction or publication of any
              Act of a Legislature, judicial proceedings, or government gazette notifications.
            </p>
          </section>

          <section className="space-y-1.5">
            <h3 className="font-semibold text-[var(--primary)] text-sm">
              Synthetic Case Disclaimer
            </h3>
            <p>
              All parties, incidents, witness statements, and corporate entities depicted in the case library
              are entirely fictional creations produced for testing legal reasoning algorithms. Any resemblance
              to actual persons, living or deceased, or actual judicial disputes is strictly coincidental.
            </p>
          </section>
        </div>

        <div className="flex justify-end pt-3 border-t border-[var(--border)]">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-white bg-[var(--primary)] rounded-[var(--radius-md)] hover:brightness-110 active:brightness-95 transition-all shadow-sm cursor-pointer"
          >
            I Understand & Acknowledge
          </button>
        </div>
      </div>
    </div>
  );
}

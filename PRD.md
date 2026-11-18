# PRD: Verdict

Version 0.1 · 18 Nov 2026 · Status: draft · Detail for each build step lives in `Phases.md`.

## Vision and one-liner

**One-liner:** A 3D courtroom where every role is its own AI agent, and the verdict is scored against a hidden truth.

Verdict lets people watch or play a full trial under Indian criminal law. The judge, lawyers, witnesses, defendant and jury are separate agents that each know only what their role should know. The verdict is 50% LLM jury and 50% three LLM judges using retrieval over law, philosophy and ethics. It runs on free-tier model APIs with automatic failover, so it costs nothing to run.

## Personas

1. **Aarav, law student (21).** Wants cross-examination and objection practice. Mock trials need too many people and too much scheduling.
2. **Meera, curious learner (28).** No legal background. Wants to see how a trial actually works and why a verdict came out the way it did.
3. **Dev, educator or AI builder (35).** Wants to run many trials, change jury makeup, and measure bias and accuracy.

## Core user stories

1. As Meera, I want to watch a complete trial so that I understand how trials work.
2. As Aarav, I want to play the defense lawyer so that I can practise cross-examining a witness.
3. As Aarav, I want to raise objections and see the judge rule so that I learn admissibility.
4. As Meera, I want to see why the verdict was reached, with cited testimony and law, so that I can trust or challenge it.
5. As Meera, I want to see what really happened after the verdict so that I know whether justice was served.
6. As Dev, I want to run the same case with different juries so that I can measure bias.
7. As Dev, I want to replay and export a finished trial so that I can analyse it.
8. As any user, I want the trial to keep going when one AI provider runs out of quota so that sessions do not break.

## Functional requirements

**P0 (v1 cannot ship without these)**

1. Create an account or start as a guest; sessions use JWT.
2. Browse a case library and start a trial from a case.
3. 3D courtroom scene with judge, two lawyers, witness, defendant, clerk and jurors.
4. Server-driven event stream: each line has speaker, text, action, camera; client acks each line before the next is sent.
5. Orchestrated trial flow: openings, witness examination, objections and rulings, closings, jury instructions, deliberation, vote, verdict.
6. Each agent sees only its allowed context (information isolation enforced in code).
7. Rules engine enforces turn order, objection limits and exhibit admissibility.
8. Sustained objections remove the testimony from juror retrieval.
9. Hidden ground truth per case; verdict is compared with it and the result is shown.
10. Verdict = 0.5 × jury share + 0.5 × mean of 3 judge probabilities, with threshold and a "hung" band.
11. LLM router with multiple keys per provider, multi-provider chains and a local fallback.
12. Law knowledge base (Constitution, BNS, BNSS, BSA) with hybrid search and enforced citations.

**P1**

13. Play as defense lawyer or prosecutor (human turn, typed questions, Objection button).
14. Juror personas, 2-3 deliberation rounds, devil's advocate, private vote before and after.
15. Judges with different philosophies running on different providers.
16. Verdict screen with reasoning, citations and disagreement score.
17. Replay of a finished trial.
18. Browser text-to-speech with a different voice per role.
19. Case generator (truth, timeline, evidence, witness knowledge slices) with validation.

**P2**

20. Play as judge or juror.
21. Bias lab: batch-run a case with different jury mixes and compare.
22. Philosophy, ethics and context collections for judges.
23. Admin view of provider and key health.
24. Realistic character models and lip sync.

## Non-functional requirements

- **Performance:** first line of a trial within 6 s of start (LLM dependent); 3D scene at 60 fps on a mid-range laptop, 30 fps minimum; a full trial in under 15 minutes.
- **Reliability:** every LLM call must resolve through the failover chain; no single provider outage ends a trial.
- **Security:** API keys only on the server and in `.env`; hashed passwords; input validation on every endpoint; rate limiting; no secrets in logs.
- **Privacy:** cases are fictional; free tiers may use prompts for training, so no real personal data is sent.
- **Accessibility:** captions for every spoken line; full keyboard control; respects reduced motion; WCAG AA contrast; voice is optional.
- **Cost:** €0 infrastructure beyond free tiers and local compute.

## Success metrics (initial targets, to calibrate)

- Truth-match rate on the 3 hand-written cases: at least 65% over 20 runs each.
- Trial completion without manual intervention: at least 90%.
- Isolation violations (juror cites struck turn, witness states unseen fact): 0 per 100 trials.
- LLM calls that get a valid response through failover: at least 99%.
- Tokens per full trial: at most 300,000.
- Retention: 30% of first-time users start a second trial within 7 days.

## Out of scope for v1

Real legal advice or any claim of legal accuracy · multiplayer · VR · mobile app · voice input · user-uploaded cases · jurisdictions other than India · appeals mode · paid plans · MetaHuman-grade characters · Redis or other extra infrastructure.

**Disclaimer shown in the app:** a simulation for education and entertainment, not legal advice. Indian criminal trials are decided by judges, so the jury is a deliberate game feature.

# Memory: session state

Update this file at the end of every session. Read it at the start of every session.

## Current Phase

Phase 8: Secondary features & evaluation (Batch D completed -> Batch E next)

## Active Goal

Implement all P2 tasks authorized across Batches A through E:
- **Batch A (Backend foundations)**: COMPLETED & VERIFIED
  1. Staged case generator with caching [P4] (Done)
  2. GET /admin/llm-status endpoint plus admin page [P8] (Done)
  3. Gap a: ADMIN_EMAILS allowlist and admin auth dependency (Done)
- **Batch B (Evaluation)**: COMPLETED & VERIFIED
  4. Headless auto-ack client (Gap b) (Done)
  5. scripts/run_batch.py for unattended runs (Done)
  6. Metrics report (scripts/report.py with Wilson CI & isolation audit) (Done)
  7. Bias lab (persona mixes and comparative evaluation) (Done)
- **Batch C (Human Lawyer Mode)**: NEXT
  8. Human lawyer WebSocket commands (examine, argue, object via HumanActionEvent)
  9. Lawyer-mode UI panel in frontend
  10. Spectator lock preventing human input in watch mode
- **Batch D (Retrieval & Generation)**:
  11. Per-turn RAG citations in examination
  12. Case generator statutory grounding improvements
- **Batch E (Polish)**:
  13. Markdown/PDF transcript export
  14. Loading/error states & accessibility pass

## Last Completed

Batch B (Evaluation pipeline & headless execution):
- Headless Auto-Ack Client (`backend/app/orchestrator/headless.py`):
  - Mock WebSocket context manager auto-acknowledging LineEvents (`handle_ack`) to allow fully unattended runs without browser UI.
  - Intercepts all emitted trial events into memory with type filter helpers.
  - 2 unit tests passing in `backend/tests/unit/test_headless_client.py`.
- Deterministic Fake LLM (`backend/app/llm/fake.py`):
  - Structured output generator covering all courtroom roles (judge, clerk, prosecutor, defense, witness, jurors, verdict judges).
  - Integrates with `record_llm_call` for accurate token and cost evaluation reporting.
- Unattended Batch Runner (`scripts/run_batch.py`):
  - Sequential execution CLI with `--case`, `--runs`, `--jurors`, `--rounds`, `--persona-mix`, `--fake-llm`, `--max-total-tokens`, `--yes`.
  - Incremental JSONL persistence with resume capability skipping already-completed run indices.
- Evaluation Metrics & Isolation Auditor (`scripts/report.py`):
  - Wilson score 95% confidence interval for truth-match rates.
  - Diagnostic aggregation metrics ($J$, $P$, Statutory Score, $|J-P|$ disagreement).
  - Exact foreign-key isolation audit (struck turn citations, unretrieved statutory citations) and heuristic witness knowledge leakage audit.
  - Outputs both machine-readable JSON and formatted GitHub alert markdown reports.
- Bias Laboratory (`scripts/bias_lab.py`):
  - Automated comparative evaluation across 3 demographic-free persona mix panels (`balanced`, `rigorous_analytic`, `intuitive_holistic`).
  - Strict compliance with ethical charter banning protected demographic attributes.
- Quality Assurance:
  - 208 backend pytest tests passing (0 failures).
  - 19 frontend Vitest tests passing (0 failures).
  - Frontend typecheck (`tsc -b`) clean.
  - ESLint clean (0 errors).
  - Ruff check & format clean on both backend/ and scripts/.
  - Mypy check clean on headless.py and fake.py.

## Decisions Log

Newest on top. Format: `YYYY-MM-DD · decision · reason`.

2026-11-20 · Configured libpq PATH discovery and pure-python psycopg fallback in conftest.py and session.py · Resolves Windows 11 Smart App Control blocking unsigned psycopg-binary wheel DLLs.
2026-11-20 · Completed Batch B evaluation suite with HeadlessAutoAckClient, batch runner, metrics report with Wilson CI, and bias lab · Fulfills Batch B evaluation requirements with 100% test pass rate.
2026-11-19 · Implemented GET /admin/llm-status and admin_required auth dependency checking ADMIN_EMAILS · Restricts LLM pool and observability metrics to designated administrators without exposing secret keys.
2026-11-19 · Implemented frontend AdminPage with table skeleton loading, error retry, empty states, and KPI cards · Fulfills Design.md specifications for system administration view.
2026-11-19 · Implemented 3-stage case generator with caching, statutory retrieval grounding, and strict validation · Fulfills Batch A [P4] requirements.
2026-11-19 · Authorized batch execution exception to Rules.md covering P2 secondary tasks in Batches A through E · Explicit user exception logged per prompt.
- Database migrations & ORM:
  - Migration `007_create_votes_and_verdicts_tables.py` creating `votes` (pre/final juror and verdict judge votes) and `verdicts` tables with foreign keys and indexes.
  - `Vote` and `Verdict` SQLAlchemy models in `backend/app/db/models/trial.py`.
- Pure voting aggregation module (`backend/app/voting/aggregation.py`):
  - Formulas: $J = \frac{\text{guilty votes}}{\text{total juror votes}}$, $P = \frac{\sum \text{guilt\_probability}}{3}$, $\text{Score} = 0.5 \times J + 0.5 \times P$, $\text{Disagreement} = |J - P|$.
  - Threshold & hung band: `guilty` if Score >= threshold; `not_guilty` if Score <= (threshold - hung_band); else `hung`.
  - BNS statutory sentencing ranges (BNS 103(1), 318(4), 117(2)).
  - Comprehensive unit test suite (`test_voting_aggregation.py`) covering all pure functions with 100% pass rate.
- Information isolation for jurors & verdict judges:
  - `build_juror_context()`: strictly filters to clean record (`admitted == True` and `struck == False`), admitted evidence, and strictly excludes secret `case.truth` and lawyer notes.
  - `build_juror_vote_prompt()`: enforces step-by-step reasoning based on juror traits/style.
  - `build_juror_deliberation_prompt()`: dynamic devil's advocate role to challenge consensus.
  - `build_verdict_judge_context()`: clean record and statutory retrieval with `role="judge"`.
  - `build_verdict_judge_prompt()`: distinct textualist, precedent, and constitutional fairness guidance.
- Orchestrator graph integration:
  - Added `deliberation_node()` and `verdict_node()` into LangGraph `StateGraph`.
  - Parallel execution via `asyncio.gather()` for pre-votes, deliberation rounds, post-votes, and judicial opinions.
  - Dispatches `VerdictEvent` and presiding judge pronouncement turn.
- REST API:
  - `GET /trials/{trial_id}/verdict` endpoint returning full verdict summary and vote breakdown.
- Frontend:
  - Rich `VerdictScreen.tsx` dialog with outcome badge, radial score gauge, threshold indicators, disagreement metrics, judicial opinions, and truth reveal tab.
- Quality assurance:
  - 193 backend pytest tests pass (0 failures).
  - 15 frontend Vitest tests pass.
  - Frontend typecheck clean (`tsc -b`).
  - Ruff check & format clean (109 files formatted).
  - Mypy check clean (34 source files).

## Decisions Log

Newest on top. Format: `YYYY-MM-DD · decision · reason`.

2026-11-19 · Implemented hybrid statutory voting aggregation Score = 0.5*J + 0.5*P with hung band and truth comparison · Aligns with Architecture.md section 10 and pure function design.
2026-11-19 · Enforced strict juror isolation ensuring only admitted, non-struck turns and admitted exhibits are accessible to jurors · Guarantees legal integrity of simulated jury deliberations.
2026-11-19 · Assigned dynamic devil's advocate role in juror deliberation rounds · Tests group consensus and ensures robust deliberation dynamics.
2026-11-19 · Created three distinct verdict judge agents (textualist, precedent, fairness) with statutory retrieval · Reflects diverse Indian judicial philosophies in bench opinions.

## Next Step

Awaiting user review of the 3 cases and approval ("go") to begin Batch C (Phase 5: Gateway, orchestrator, live judge in 3D):
1. Propose and add the two new tasks to TASKS.md under P1 [P5]:
   - POST /trials and GET /trials/{id}
   - Minimal frontend trial setup: case list, Start button, and trial screen
2. `trials`, `agents`, `turns` migrations (with FK from `llm_calls.trial_id` to `trials.id`)
3. WebSocket endpoint, auth handshake, and event schemas
4. Orchestrator skeleton with LangGraph (setup, openings, closings)
5. Context filter and prompt for judge and clerk
6. Send-then-wait-for-ack loop with timeout and client dead pause
7. Port prototype courtroom furniture and lighting to React Three Fiber
8. Placeholder characters with sit, stand, talk, and point states
9. Event player and queue on client with ack sending
10. Camera director with wide, close, and jury shots, and captions overlay

## Decisions Log

Newest on top. Format: `YYYY-MM-DD · decision · reason`.

2026-11-19 · Implemented witness memory builder and strict isolation tests verifying witnesses have zero recall of events outside saw_event_ids · Meets Phase 4 Definition of Done and context boundary security.
2026-11-19 · Implemented GET /cases and GET /cases/{id} supporting slug and UUID lookups while hiding secret truth from public endpoints · Adheres to Architecture.md API conventions.
2026-11-19 · Created 3 hand-made post-2024-07-01 BNS cases (BNS 103(1) murder, BNS 318(4) cheating, BNS 117(2) grievous hurt) with timeline ground truth, inadmissible exhibits (BSA 63, BSA 60/61, BSA 55/57), and witness secrecy lists · Fulfills Batch B case requirements.
2026-11-19 · Implemented case validation engine (app.cases.validator) and scripts/load_cases.py loader with dry-run check-only mode · Ensures deterministic database state and schema compliance.
2026-11-19 · Implemented hybrid retrieval with exact lookup, weighted FTS, vector search, RRF (k=60) and citation-aware reranking achieving 92.0% top-5 benchmark accuracy · Meets Phase 3 Definition of Done.
2026-11-19 · Added deterministic SHA-256 FakeEmbedder (1024-dim) and lexical FakeReranker for zero-download test execution · Complies with prompt constraint that CI/tests never download external models.
2026-11-19 · Ingested BNS, BNSS, BSA, Constitution (2,252 chunks total) with IPC concordance mappings and Section 52(1)(q) public domain license tags · Completes legal corpus ingestion for Batch A.
2026-11-18 · Implemented SOURCES.md gate, PyMuPDF extraction, sub-section token splitting (>512 tokens) and idempotent upsert on (act, section_no, valid_from) · Fulfills law ingestion requirements for Batch A.
2026-11-18 · Authorized sequential execution of P1 core features across Phases 3 to 7 (Batches A through E) with checkpoints after each batch · Explicit user exception to Rules.md single-phase constraint.
2026-11-18 · Implemented statutory act chunker and CLI ingestion script under Section 52(1)(q) Indian Copyright Act public domain provisions · Complies with Rules.md requirement to source official legislative text without memorization.
2026-11-18 · Created cases, evidence, and witnesses models and migration 004_cases_evidence_witnesses with CASCADE foreign keys and reliability check constraint · Implements Architecture.md section 3 data model.
2026-11-18 · Created knowledge_chunks model and migration 003_knowledge_chunks with HNSW vector, GIN tsv, and lookup indexes, plus added embedding_model and ingested_at columns · Fulfills pre-agreed schema enhancement decision and updated Architecture.md.
2026-11-18 · Created llm_calls migration (002_llm_calls) with trial_id as nullable UUID without FK · Pre-agreed decision; trials table does not exist until Phase 5.
2026-11-18 · Implemented structured JSON retry and provider fallthrough with 94% test coverage on app.llm · Meets prompt specification and Rules.md structured output mandate.
2026-11-18 · Implemented KeyPool escalating cooldown min(60 * 2**fails, 86400) and OpenAI-compatible client for Gemini, Groq, OpenRouter, Ollama · Ensures zero outage on free tier quota exhaustion.
2026-11-18 · Pinned exact versions in backend/requirements.txt and frontend/package.json via check_versions.py · Architecture.md says to check registries and pin exact patch versions.
2026-11-18 · Created GitHub Actions CI matrix with PostgreSQL 17 + pgvector service container, Python 3.12, Node 22 LTS, and complete lint/type/test/build validation.
2026-11-18 · Configured Vitest, Testing Library, and ESLint flat config on frontend alongside ruff/mypy/pytest on backend · All suites passing.
2026-11-18 · Integrated Three.js and React Three Fiber with CourtroomCanvas and Floor components · Complies with Rules.md 3D component isolation requirements.
2026-11-18 · Scaffolded React 19 + Vite 6 + Tailwind CSS v4 frontend with exact Design.md courtroom design tokens and strict TypeScript · Validated production build with zero errors.
2026-11-18 · Implemented get_current_user HTTPBearer auth dependency and guest session endpoint with anonymous UUID generation · Completes Batch A (Phase 1 Backend).
2026-11-18 · Implemented Argon2id password hashing and PyJWT token generation with extra="forbid" Pydantic schemas · Adheres to Rules.md security requirements.
2026-11-18 · Initialized Alembic with async SQLAlchemy 2.0 and created 001_users migration with vector and citext extensions · Matches Architecture.md data model.
2026-11-18 · Implemented standard Success/Error response envelopes and FastAPI factory with X-Request-ID middleware · Complies with Architecture.md section 4.
2026-11-18 · Authorized cross-phase batch execution for P0 tasks (Batches A, B, C, D) with checkpoint after each batch · User explicit exception to Rules.md.
2026-11-18 · Selected pgvector/pgvector:pg17 Docker image with healthcheck and persistent volume · Fulfills ADR-1 requirement for PostgreSQL 17 + pgvector.
2026-11-18 · Initialized Git repository and created directory layout with .gitkeep placeholders · Establish project baseline according to Architecture.md directory specifications.

## Blockers / Open Questions

- [ ] Which free model ids will fill `CHAIN_STRONG`, `CHAIN_MID`, `CHAIN_SMALL`? Check each provider console before Phase 2.
- [ ] Will the local embedding model run on the development machine? (Needs enough RAM; decide before Phase 3.)
- [ ] Keep the jury as a game feature or redesign as a bench of judges? (Currently: keep, with a disclaimer.)
- [ ] Source and license check for each law text before ingestion.

## Progress

### Phase 1: Project setup, scaffold and auth
- [x] Create repo structure and root `README.md`
- [x] Add `docker-compose.yml` (Postgres 17 + pgvector) and `.env.example`
- [x] Scaffold FastAPI app with config, `/health` and response envelope
- [x] Set up SQLAlchemy, Alembic and the `users` migration
- [x] Implement register, login and guest endpoints with JWT
- [x] Scaffold frontend (Vite, React, TypeScript, Tailwind) with empty 3D canvas
- [x] Set up linting, type checks and test runners
- [x] Add GitHub Actions CI
- [x] Run version check, pin exact versions, log them here

### Pinned Versions (2026-11-18, via `scripts/check_versions.py`)

| Component | Architecture Baseline | Pinned Version |
|---|---|---|
| Python | 3.12 | 3.14.4 (dev machine; CI pins 3.12) |
| FastAPI | 0.115+ | 0.136.0 |
| Uvicorn | 0.30+ | 0.44.0 |
| Pydantic | 2.x | 2.13.3 |
| Pydantic-Settings | 2.x | 2.16.0 |
| SQLAlchemy | 2.0 | 2.0.49 |
| Alembic | 1.x | 1.18.4 |
| psycopg | 3.x | 3.3.8 |
| argon2-cffi | modern | 25.1.0 |
| PyJWT | 2.x | 2.15.1 |
| email-validator | 2.x | 2.3.0 |
| httpx | 0.27+ | 0.28.1 |
| pytest | latest | 8.4.2 |
| pytest-asyncio | latest | 1.3.0 |
| ruff | latest | 0.17.1 |
| mypy | latest | 1.20.2 |
| Node.js | 22 LTS | 24.14.1 (dev machine; CI pins 22) |
| React | 19 | 19.3.1 |
| Vite | 7 (or 6+) | 6.4.6 |
| TypeScript | 5.x | 5.9.3 |
| Tailwind CSS | 4.x | 4.3.5 |
| Zustand | 5.x | 5.1.0 |
| Three.js | 0.17x+ | 0.187.0 |
| @react-three/fiber | 9 | 9.8.2 |
| @react-three/drei | latest | 10.7.9 |
| Vitest | latest | 5.1.1 |
| ESLint | latest | 10.15.0 |

### Phase 2: LLM router with failover
- [x] Key pool class with cooldown and escalating backoff, plus unit tests
- [x] Provider client for OpenAI-compatible endpoints (Gemini, Groq, OpenRouter, Ollama)
- [x] Tier chain parser and `chat(tier, messages)` with failover
- [x] JSON validation with one retry, then fall through the chain
- [x] Forced-failover tests: bad key, quota, timeout, all providers down (94% coverage)
- [x] `llm_calls` migration and call logging with `key_alias`

### Phase 3: Law knowledge base and retrieval (Foundation)
- [x] `knowledge_chunks` migration with HNSW, GIN and lookup indexes

### Phase 4: Cases and ground truth (Foundation)
- [x] Case, evidence and witness migrations and the case JSON schema

### Later phases (expand the checklist from `Phases.md` when you reach each one)
- [ ] Phase 3: Law knowledge base and retrieval (Ingestion and retrieval functions)
- [ ] Phase 4: Cases and ground truth (Handwritten cases and witness builder)
- [ ] Phase 5: Gateway, orchestrator and a live judge in 3D
- [ ] Phase 6: Lawyers, witnesses, objections and the record
- [ ] Phase 7: Jury, verdict judges, voting and scoring
- [ ] Phase 8: Human modes, voice, replay and evaluation

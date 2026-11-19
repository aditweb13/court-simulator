# Memory: session state

Update this file at the end of every session. Read it at the start of every session.

## Current Phase

Phase 5: Gateway, orchestrator, live judge in 3D (COMPLETED) -> Phase 6: Lawyers, witnesses, objections, and the record (NEXT)

## Active Goal

Phase 5 Definition of Done achieved:
Starting a trial in the browser plays a live LLM-generated opening from the judge in the 3D scene, in order, with captions, and the server waits for each ack.

Ready to begin Phase 6 tasks:
1. Prosecutor and defense agents with adversarial prompts and private notes
2. Witness and defendant agents using their knowledge slices
3. Rules engine: turn order, objection quota, admissibility, with tests
4. Objection and ruling flow in the graph
5. `turn_embeddings` migration and embedding of each new turn
6. Mark struck turns on sustained objections
7. Witness examination loop (direct, cross, redirect)

## Last Completed

Phase 5 (Gateway, Orchestrator, and Live Judge in 3D):
- Database migrations & models for `trials`, `agents`, `turns` with foreign key relations.
- REST endpoints `POST /trials` and `GET /trials/{id}` with agent seeding (Judge, Clerk, Prosecutor, Defense, Accused, Witnesses, 7 Jurors, 3 Verdict Judges).
- WebSocket endpoint `/ws/v1/trials/{trial_id}` with 5-second auth handshake, event schemas (`line`, `ruling`, `state`, `prompt`, `verdict`, `error`), and connection manager.
- Orchestrator skeleton with LangGraph (`StateGraph`, `CourtroomState`, `setup_node`, `openings_node`, `closings_node`).
- Context filters and prompt builders (`build_judge_context()`, `build_clerk_context()`) enforcing strict information isolation (judge never sees case truth, clerk has minimal docket data).
- Send-then-wait-for-ack loop with timeout (`ack_timeout_seconds=10.0`), auto-pause on dead client, and fast-path ack dictionary to prevent race conditions.
- React Three Fiber 3D Courtroom Scene: Dais, Judge's bench, gavel, clerk desk, witness stand, counsel tables (prosecution/defense styling), 7-seat tiered jury box, spectator gallery pews, warm illumination and architectural walls.
- Stylized placeholder humanoid characters (`Character.tsx`, `CourtroomCharacters.tsx`) supporting `sit`, `stand`, `talk`, and `point` states, plus judicial and advocate robes and legal neck tabs.
- Camera Director (`CameraDirector.tsx`, `shots.ts`) with shot presets (`wide`, `judge`, `witness`, `prosecution`, `defense`, `jury`, `clerk`), smooth lerping, and instant cut behavior on `prefers-reduced-motion`.
- Event player and queue (`trialWs.ts`, `schemas.ts`, `trialStore.ts`) with dynamic character-count reading pace, auto-ack dispatch, and manual turn advance.
- Full courtroom UI: `Captions.tsx`, `CameraControls.tsx`, `Transcript.tsx`, `TrialControls.tsx`, and responsive 12-column layout in `App.tsx`.
- 100% tests passing (15 Python unit tests, 12 Vitest frontend tests), ruff, mypy, tsc, and eslint all completely clean.

## Decisions Log

Newest on top. Format: `YYYY-MM-DD · decision · reason`.

2026-11-19 · Implemented full Phase 5 frontend (characters, camera director, event player, captions, transcript, controls) and integrated WebSocket auto-start for orchestrator · Satisfies Phase 5 Definition of Done.
2026-11-19 · Added send-then-wait-for-ack loop with ack timeout (10s) and fast-path resolution in ConnectionManager · Ensures server pauses when client drops and prevents turn racing.
2026-11-19 · Implemented context isolation for Judge and Clerk: judge gets public case facts, admitted evidence, and statutory chunks only; clerk gets minimal case docket data · Prevents hallucinated bias and truth leakage.
2026-11-19 · Built LangGraph orchestrator state graph (setup -> openings -> closings) with Pydantic structured output models and chat() routing · Establishes deterministic trial flow.

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

# Memory: session state

Update this file at the end of every session. Read it at the start of every session.

## Current Phase

Phase 2: LLM router with failover (Batch C complete)

## Active Goal

Complete P0 blocker tasks: finished Batch C (LLM Router), prepare for Batch D (Schema migrations: knowledge_chunks, cases/evidence/witnesses).

## Last Completed

Batch C complete (Tasks 12-17): KeyPool, OpenAI-compatible client, tier chain parser, chat() failover router, Pydantic JSON retry, forced-failover integration test suite (94% coverage on app.llm), and llm_calls migration with key_alias logging.

## Next Step

Batch D: Schema migrations (Tasks 18-19) — knowledge_chunks with HNSW/GIN indexes, then cases/evidence/witnesses plus case JSON schema.

## Decisions Log

Newest on top. Format: `YYYY-MM-DD · decision · reason`.

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

### Later phases (expand the checklist from `Phases.md` when you reach each one)
- [ ] Phase 3: Law knowledge base and retrieval
- [ ] Phase 4: Cases and ground truth
- [ ] Phase 5: Gateway, orchestrator and a live judge in 3D
- [ ] Phase 6: Lawyers, witnesses, objections and the record
- [ ] Phase 7: Jury, verdict judges, voting and scoring
- [ ] Phase 8: Human modes, voice, replay and evaluation

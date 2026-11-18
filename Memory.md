# Memory: session state

Update this file at the end of every session. Read it at the start of every session.

## Current Phase

Phase 1: Project setup, scaffold and auth

## Active Goal

Get the repo, database, backend, frontend scaffold, auth and CI running locally.

## Last Completed

Added `docker-compose.yml` (Postgres 17 + pgvector) and `.env.example` with all variable names (Task 2 in `TASKS.md`).

## Next Step

FastAPI app factory, settings loader, `/health` route and the response/error envelope (Task 3 in `TASKS.md`).

## Decisions Log

Newest on top. Format: `YYYY-MM-DD · decision · reason`.

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
- [ ] Scaffold FastAPI app with config, `/health` and response envelope
- [ ] Set up SQLAlchemy, Alembic and the `users` migration
- [ ] Implement register, login and guest endpoints with JWT
- [ ] Scaffold frontend (Vite, React, TypeScript, Tailwind) with empty 3D canvas
- [ ] Set up linting, type checks and test runners
- [ ] Add GitHub Actions CI
- [ ] Run version check, pin exact versions, log them here

### Later phases (expand the checklist from `Phases.md` when you reach each one)
- [ ] Phase 2: LLM router with failover
- [ ] Phase 3: Law knowledge base and retrieval
- [ ] Phase 4: Cases and ground truth
- [ ] Phase 5: Gateway, orchestrator and a live judge in 3D
- [ ] Phase 6: Lawyers, witnesses, objections and the record
- [ ] Phase 7: Jury, verdict judges, voting and scoring
- [ ] Phase 8: Human modes, voice, replay and evaluation

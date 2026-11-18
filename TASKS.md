# TASKS: queue

Each task fits in one agent session (under about 2 hours). `[Pn]` shows the phase in `Phases.md`. Take the first unchecked task in the highest priority group unless told otherwise. Check a task off only when it meets the Definition of Done in `Phases.md`.

## P0: blockers and must-haves

- [x] [P1] Create repo structure from `Architecture.md` and write the root `README.md`
- [x] [P1] Add `docker-compose.yml` (Postgres 17 + pgvector) and `.env.example` with all variable names
- [x] [P1] FastAPI app factory, settings loader, `/health` route and the response/error envelope
- [x] [P1] SQLAlchemy session setup, Alembic init and the `users` migration
- [x] [P1] Register and login endpoints with password hashing and JWT
- [x] [P1] Guest session endpoint and an auth dependency for protected routes
- [x] [P1] Vite + React + TypeScript + Tailwind scaffold with `globals.css` tokens from `Design.md`
- [x] [P1] Empty 3D canvas component rendering a placeholder floor
- [x] [P1] Lint, type-check and test runners for backend and frontend
- [x] [P1] GitHub Actions CI workflow running all checks
- [x] [P1] `scripts/check_versions.py` to compare baselines with registries, then pin and log versions in `Memory.md`
- [x] [P2] Key pool class with cooldown and escalating backoff, plus unit tests
- [x] [P2] Provider client for OpenAI-compatible endpoints (Gemini, Groq, OpenRouter, Ollama)
- [x] [P2] Tier chain parser and `chat(tier, messages)` with failover
- [x] [P2] JSON validation with one retry, then fall through the chain
- [x] [P2] Forced-failover tests: bad key, quota, timeout, all providers down
- [x] [P2] `llm_calls` migration and call logging with `key_alias`
- [x] [P3] `knowledge_chunks` migration with HNSW, GIN and lookup indexes
- [x] [P4] Case, evidence and witness migrations and the case JSON schema

## P1: core features

- [x] [P3] Ingestion script: clean and chunk one act by section with metadata
- [x] [P3] Ingest BNS, then BNSS, then BSA (one task each, check licenses first)
- [x] [P3] Ingest the Constitution, with Part III and Articles 20-22 tagged
- [x] [P3] IPC to BNS mapping table and loader
- [ ] [P3] Local embedding model wrapper (bge-m3) with batching
- [ ] [P3] Reranker wrapper (bge-reranker-v2-m3)
- [ ] [P3] Hybrid retrieval function with `audience` and `domain` filters
- [ ] [P3] Citation checker that rejects sections not in the retrieved chunks
- [ ] [P3] Retrieval test set (50 questions) and an accuracy script
- [ ] [P4] Write hand-made case 1 and the loader script
- [ ] [P4] Write hand-made cases 2 and 3
- [ ] [P4] `GET /cases` and `GET /cases/{id}` endpoints
- [ ] [P4] Witness memory builder from `saw_event_ids` and its isolation test
- [ ] [P4] Case validation checks in code
- [ ] [P5] `trials`, `agents`, `turns` migrations (add deferred FK from `llm_calls.trial_id` to `trials.id`)
- [ ] [P5] `POST /trials` and `GET /trials/{id}` (create trial from case & mode, store juror_count, rounds, threshold, hung_band)
- [ ] [P5] WebSocket endpoint, auth handshake and event schemas
- [ ] [P5] Orchestrator skeleton with LangGraph (setup, openings, closings)
- [ ] [P5] Context filter and prompt for the judge and the clerk
- [ ] [P5] Send-then-wait-for-ack loop with timeout and a pause on dead client
- [ ] [P5] Port the prototype courtroom furniture and lighting to the React scene
- [ ] [P5] Placeholder characters with sit, stand, talk and point states
- [ ] [P5] Event player and queue on the client, with ack sending
- [ ] [P5] Camera director with wide, close and jury shots, and captions overlay
- [ ] [P5] Minimal frontend trial setup: case list, Start button, and trial screen
- [ ] [P6] Prosecutor and defense agents with adversarial prompts and private notes
- [ ] [P6] Witness and defendant agents using their knowledge slices
- [ ] [P6] Rules engine: turn order, objection quota, admissibility, with tests
- [ ] [P6] Objection and ruling flow in the graph
- [ ] [P6] `turn_embeddings` migration and embedding of each new turn
- [ ] [P6] Mark struck turns on sustained objections
- [ ] [P6] Witness examination loop (direct, cross, redirect)
- [ ] [P6] Isolation test suite for witnesses, lawyers and the record
- [ ] [P7] Juror personas and the step-by-step reasoning prompt
- [ ] [P7] Juror retrieval limited to admitted, non-struck turns, plus its isolation test
- [ ] [P7] Deliberation rounds with a devil's advocate, run in parallel
- [ ] [P7] Private pre- and post-deliberation votes
- [ ] [P7] Three verdict judge agents with different philosophies and starting providers
- [ ] [P7] Aggregation module (0.5 × J + 0.5 × P, threshold, hung band, disagreement) with unit tests
- [ ] [P7] `votes` and `verdicts` migrations and persistence
- [ ] [P7] Truth comparison and the verdict event
- [ ] [P7] Verdict screen with reasoning and citations

## P2: secondary

- [ ] [P4] Staged case generator (truth, evidence, witnesses) with caching
- [ ] [P8] Human lawyer mode: prompt events and typed questions
- [ ] [P8] Objection button with keyboard shortcut and quota display
- [ ] [P8] Browser text-to-speech with per-role voices and a voice toggle
- [ ] [P8] Replay endpoint streaming stored turns
- [ ] [P8] Replay UI with a play and pause control
- [ ] [P8] `scripts/run_batch.py` for unattended runs
- [ ] [P8] Metrics report: truth-match, cost, isolation violations, disagreement
- [ ] [P8] `GET /admin/llm-status` page showing pool health
- [ ] [P8] Play as judge mode
- [ ] [P8] Play as juror mode
- [ ] [P8] Bias lab: batch runs with different juror persona mixes

## P3: nice-to-have and polish

- [ ] [P8] Replace placeholder characters with rigged models and animation clips
- [ ] [P8] Lip sync driven by audio volume
- [ ] [P8] Gavel, murmur and footstep sounds
- [ ] [P8] Gallery reactions and juror reaction animations
- [ ] [P8] Lighting and materials pass
- [ ] [P8] Accessibility pass against the checklist in `Design.md`
- [ ] [P8] Philosophy, ethics and context collections for the verdict judges
- [ ] [P8] Disclaimer screens and README update
- [ ] [P8] Dark and light theme toggle

# Phases: Verdict delivery plan

Eight phases, ordered by dependency (DB, then API, then UI, then integrations, then polish). Each fits in 1-2 focused AI sessions. If a phase grows past that, split it.

## Phase 1: Project setup, scaffold and auth

- [ ] Create the repo structure from `Architecture.md` and a root `README.md`
- [ ] Add `docker-compose.yml` (Postgres 17 + pgvector) and `.env.example`
- [ ] Scaffold the FastAPI app with config loading, `/health` and the response envelope
- [ ] Set up SQLAlchemy, Alembic and the first migration (`users`)
- [ ] Implement register, login and guest endpoints with JWT
- [ ] Scaffold the frontend (Vite, React, TypeScript, Tailwind) with an empty 3D canvas
- [ ] Set up linting, type checks and test runners for both sides
- [ ] Add the GitHub Actions CI workflow
- [ ] Run the version check script, pin exact versions, log them in `Memory.md`

**Done when:** `docker compose up`, the backend and the frontend all start locally, a user can register and log in, `/health` returns OK, and CI is green.

## Phase 2: LLM router with failover

- [ ] Implement key pools with cooldown and escalating backoff
- [ ] Implement the provider clients through OpenAI-compatible endpoints (Gemini, Groq, OpenRouter, Ollama)
- [ ] Parse tier chains (`CHAIN_STRONG`, `CHAIN_MID`, `CHAIN_SMALL`) from `.env`
- [ ] Add JSON response validation with one retry, then fall through the chain
- [ ] Log each call to `llm_calls` with a `key_alias`
- [ ] Add `GET /admin/llm-status` showing pools and cooldowns
- [ ] Write the forced-failover tests (bad key, quota, timeout, all down)

**Done when:** the router returns an answer when the first key is invalid, the first provider is out of quota, and when only the local model is left; all failover tests pass.

## Phase 3: Law knowledge base and retrieval

- [ ] Migration for `knowledge_chunks` with HNSW, GIN and lookup indexes
- [ ] Write the ingestion script (clean text, chunk by section, add metadata)
- [ ] Ingest the Constitution, BNS, BNSS and BSA plus the IPC to BNS mapping
- [ ] Add the local embedding model and reranker wrappers
- [ ] Implement hybrid retrieval (exact lookup, full-text, vector, merge, rerank) with role filters
- [ ] Implement citation checking (every cited section must exist in retrieved chunks)
- [ ] Build a test set of 50 questions with known answers in `data/eval/`

**Done when:** at least 90% of the 50 test questions return the right section in the top 5, and a cited section that was not retrieved is rejected.

## Phase 4: Cases and ground truth

- [ ] Migrations for `cases`, `evidence`, `witnesses`
- [ ] Define the case JSON schema (truth, timeline, evidence, witnesses)
- [ ] Write 3 hand-made cases and a loader script
- [ ] Add `GET /cases` and `GET /cases/{id}`
- [ ] Derive each witness memory from `saw_event_ids`
- [ ] Add case validation checks in code
- [ ] Implement the staged case generator and cache its output

**Done when:** three cases load and validate, a witness test asks about an event outside `saw_event_ids` and gets no knowledge of it, and one generated case passes validation.

## Phase 5: Gateway, orchestrator and a live judge in 3D

- [ ] Migrations for `trials`, `agents`, `turns`
- [ ] Define the WebSocket event schemas and the auth handshake
- [ ] Build the orchestrator skeleton (LangGraph states: setup, openings, closings)
- [ ] Write the context filters and prompt for the judge and the clerk
- [ ] Implement send-then-wait-for-ack with timeout
- [ ] Port the prototype scene into the React scene (bench, stand, tables, jury box)
- [ ] Build the event player, camera director and captions

**Done when:** starting a trial in the browser plays a live LLM-generated opening from the judge in the 3D scene, in order, with captions, and the server waits for each ack.

## Phase 6: Lawyers, witnesses, objections and the record

- [ ] Prosecutor and defense agents with adversarial prompts and private notes
- [ ] Witness and defendant agents using their knowledge slices
- [ ] Rules engine (turn order, objection quota, admissibility)
- [ ] Objection and ruling flow in the graph
- [ ] Embed each turn into `turn_embeddings`; mark struck turns on sustained objections
- [ ] Witness examination loop (direct, cross, redirect)
- [ ] Isolation tests for witnesses and lawyers

**Done when:** a full examination of one witness runs with at least one objection ruled on, the struck testimony is flagged, and the isolation tests pass.

## Phase 7: Jury, verdict judges, voting and scoring

- [ ] Juror personas and the step-by-step reasoning prompt
- [ ] Juror retrieval limited to admitted, non-struck turns
- [ ] Deliberation rounds with a devil's advocate, run in parallel
- [ ] Private votes before and after deliberation
- [ ] Three verdict judges with different philosophies and starting providers
- [ ] Aggregation: 0.5 × J + 0.5 × P, threshold, hung band, disagreement
- [ ] Truth comparison, `votes` and `verdicts` tables, and verdict events
- [ ] Verdict screen with reasoning and citations

**Done when:** a full trial runs from opening to a cited verdict, the aggregator unit tests pass, no juror cites a struck turn, and the verdict is compared with the hidden truth.

## Phase 8: Human modes, voice, replay and evaluation

- [ ] Human lawyer mode (typed questions, Objection button, prompt events)
- [ ] Browser text-to-speech with per-role voices
- [ ] Replay endpoint and replay UI
- [ ] Batch runner script (`scripts/run_batch.py`)
- [ ] Metrics report: truth-match, cost, isolation violations, jury vs judge disagreement
- [ ] Character models, animation clips and polish (lighting, sound)
- [ ] Disclaimer, accessibility pass, README update

**Done when:** you can play as the defense lawyer and cross-examine a witness, 20 unattended trials of one case produce a metrics report, and the accessibility checks in `Design.md` pass.

## Definition of Done (every task and phase)

- [ ] Lints pass (`ruff`, `eslint`) and type checks pass (`mypy`, `tsc`)
- [ ] All tests are green, including isolation tests
- [ ] No `TODO`, debug prints or commented-out code
- [ ] `.env.example`, docs and `Memory.md` are updated
- [ ] No secrets in the diff
- [ ] The phase **Done when** line is demonstrably true

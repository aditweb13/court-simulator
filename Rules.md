# Rules for the AI coding agent

Copy this file to `CLAUDE.md` or `AGENTS.md` if your tool expects that name. Read `PRD.md`, `Architecture.md`, `Phases.md`, `Memory.md` and `TASKS.md` before doing any work.

## USE

- Python 3.12 with full type hints; Pydantic v2 models for every request, response, event and LLM output.
- FastAPI routers per resource under `backend/app/api/`, with the JSON envelope and error codes from `Architecture.md`.
- SQLAlchemy 2.0 with Alembic migrations for **all** database access. One migration per schema change.
- **One LLM entry point:** `backend/app/llm/router.py`. Every model call goes through `chat(tier, messages)`.
- **One context entry point per role** in `backend/app/context/`. An agent only receives what its filter returns.
- Rules (turn order, objection quotas, admissibility) as pure functions in `backend/app/rules/`, never inside prompts.
- Structured JSON output for every agent, validated with Pydantic, with one retry on invalid output.
- Settings only through `backend/app/config.py`, read from environment variables.
- Frontend: React function components, TypeScript strict mode, Zustand for shared state, Tailwind classes with the tokens in `Design.md`, and `cn()` for conditional classes.
- 3D: one component per scene object; camera shots defined as data in `frontend/src/camera/`.
- Small, focused commits. One task from `TASKS.md` per commit where possible.

## AVOID

- No new libraries or UI frameworks unless approved (see AI boundaries).
- No direct calls to Gemini, Groq, OpenRouter or Ollama outside `llm/router.py`.
- No agent reading the full transcript, the database or another agent's memory directly.
- No legal text, section numbers or case citations written from model memory. Use retrieved chunks only.
- No over-abstracting one-off helpers; no generic base classes without two real users.
- No editing files outside the requested scope; no reformatting unrelated code.
- No `localStorage` for anything security-related; no secrets in the frontend bundle.
- No `TODO` or commented-out code left behind at the end of a task.
- No changing the 50/50 voting rule, thresholds or isolation rules without an entry in the Decisions Log.

## AI BOUNDARIES

1. Read `PRD.md` and `Architecture.md` before implementing; read `Memory.md` at the start of every session.
2. Follow `Phases.md`: finish the current phase, meeting its **Done when** line, before starting the next.
3. Work from `TASKS.md`. Take the first unchecked task in the highest priority group unless told otherwise.
4. Plan first (a short list of files and steps) before touching more than 3 files, and wait for approval on large plans.
5. Do not install or upgrade packages without explicit approval. Name the package, version and reason when asking.
6. Stop after 2 failed attempts at the same problem, and report what was tried, the error and your best guess.
7. Never invent API model ids, endpoints or version numbers. Check the provider docs or ask.
8. Never commit `.env` or any real key. Update `.env.example` when you add a variable.
9. Update `Memory.md` at the end of every session: last completed, next step, decisions, blockers, progress.
10. When requirements are unclear, ask one specific question instead of guessing.

## Security

- Validate all input with Pydantic; reject unknown fields on write endpoints.
- Secrets only from environment variables. Never log keys, tokens or full prompts containing user data; log a `key_alias` such as `gemini#1`.
- Hash passwords with a modern algorithm (argon2 or bcrypt). JWTs have an expiry. Rate-limit auth routes.
- Use parameterized queries through the ORM only. No string-built SQL.
- Avoid N+1 queries: load related rows with joins or `selectinload`, and batch embedding and vote inserts.
- Retrieval must always apply role filters (`audience`) and, for jurors, `admitted = true AND struck = false`.
- Cap LLM retries and total calls per trial so a bug cannot burn a free quota.
- Treat all LLM output as untrusted: validate its shape, escape it before rendering in the UI.

## Testing

- Every new function in `rules/`, `voting/`, `context/` and `llm/` needs unit tests. Target 90% line coverage on these four, 80% overall backend, and meaningful tests on frontend event handling.
- **Isolation tests are mandatory** and live in `backend/tests/isolation/`. They check that jurors never retrieve struck turns, witnesses never state unseen facts, and no agent receives another agent's private memory.
- The router needs a forced-failover test: bad key, quota error, timeout, all providers down.
- Naming: backend `test_<module>_<behaviour>.py`; frontend `<Component>.test.tsx`; integration tests in `tests/integration/`.
- LLM calls are mocked in tests. A small set of marked tests (`@pytest.mark.live`) may use real keys and are never run in CI.
- A task is not done until `ruff`, `mypy`, `pytest`, `eslint`, `tsc` and `vitest` pass.

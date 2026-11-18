# Verdict

> A 3D courtroom simulator where every role is its own AI agent, and the verdict is scored against a hidden truth.

Verdict simulates complete criminal trials under Indian criminal law (Bharatiya Nyaya Sanhita, Bharatiya Nagarik Suraksha Sanhita, Bharatiya Sakshya Adhiniyam, and the Constitution of India). The judge, prosecution, defense, witnesses, defendant, clerk, and jurors operate as distinct AI agents, each strictly isolated to see only their legally permissible context. The final verdict combines a 50% jury vote share with a 50% consensus of three judicial philosophies (utilitarian, deontological, retributive/restorative).

## System Architecture

- **Backend:** Python 3.12, FastAPI, LangGraph orchestrator, SQLAlchemy 2.0 with Alembic, Pydantic v2.
- **Database & Retrieval:** PostgreSQL 17 with `pgvector` for hybrid vector/text retrieval and turn embeddings.
- **LLM Infrastructure:** Multi-provider tier router (Gemini, Groq, OpenRouter, Ollama) with key cooldowns and failover.
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Zustand, Three.js / React Three Fiber.
- **Design Tokens:** Warm courtroom palette (wood, parchment, brass) compliant with WCAG AA.

## Project Structure

```
verdict/
  PRD.md Architecture.md Rules.md Phases.md Design.md Memory.md TASKS.md
  .env.example                 # Environment variable templates
  docker-compose.yml           # PostgreSQL 17 + pgvector container
  frontend/
    src/
      scene/                   # 3D courtroom scene, furniture, lighting
      characters/              # Character components and animation states
      camera/                  # Camera director shot presets
      events/                  # WebSocket client and event queue
      ui/                      # React UI overlays, captions, controls
      store/                   # Zustand state stores
      styles/                  # Tailwind design tokens & globals.css
    tests/                     # Frontend unit and component tests
  backend/
    app/
      main.py                  # FastAPI app entrypoint
      config.py                # Environment configuration
      api/                     # REST API routers (v1)
      ws/                      # WebSocket endpoint and event schemas
      orchestrator/            # LangGraph state machine and turn loop
      rules/                   # Pure-function courtroom rules engine
      context/                 # Information isolation filters per role
      agents/                  # Agent prompts and output schemas
      llm/                     # Multi-provider router and key manager
      rag/                     # Knowledge ingestion, chunking, retrieval
      voting/                  # Jury and judicial vote aggregation
      casegen/                 # Case generation and validation
      scoring/                 # Ground truth vs verdict scoring
      db/                      # SQLAlchemy models, session, migrations
      schemas/                 # Pydantic request/response schemas
    tests/
      unit/                    # Unit tests
      integration/             # Integration tests
      isolation/               # Strict information isolation tests
  data/
    law_corpus/                # Ingested statutes and legal texts
    cases/                     # Hand-written and generated cases
    eval/                      # Benchmark test sets
  scripts/                     # Ingestion, validation, and batch scripts
  .github/workflows/           # CI pipelines
```

## Getting Started (Phase 1)

### Prerequisites

- Python 3.12+
- Node.js 22 LTS+
- Docker & Docker Compose
- Git

### Quickstart

1. **Clone repository & prepare environment:**
   ```bash
   cp .env.example .env
   ```
2. **Start Database:**
   ```bash
   docker compose up -d
   ```
3. **Backend setup:**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   alembic upgrade head
   uvicorn app.main:app --reload --port 8000
   ```
4. **Frontend setup:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Disclaimer

Verdict is an educational and entertainment simulation, **not legal advice**. Indian criminal trials in reality are decided exclusively by judges; the jury is an intentional game feature designed to explore multi-agent deliberation and bias analysis.

# Verdict: Indian BNS 2023 Courtroom Trial Simulator

An autonomous multi-agent legal reasoning and courtroom simulation platform modeled upon India's modernized criminal justice framework: the **Bharatiya Nyaya Sanhita, 2023 (BNS)**, the **Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)**, and the **Bharatiya Sakshya Adhiniyam, 2023 (BSA)**.

---

## 🏛️ System Overview

**Verdict** simulates complete, adversarial Sessions Court criminal trials in an interactive 3D courtroom environment. Autonomous AI agents assume the roles of judge, prosecution, defense counsel, witnesses, empaneled jurors, and verdict judges—engaging in statutory examination, real-time evidentiary objections, secret deliberations, and cited judicial opinions.

### Key Capabilities
- **Multi-Agent Orchestration**: State graph orchestration via LangGraph coordinating opening statements, direct examination, cross-examination, objection hearings, closing arguments, jury deliberation, and verdict pronouncements.
- **Strict Information Isolation**: Cryptographically partitioned context filters ensuring witnesses possess zero recall outside witnessed events, lawyers have private trial strategies, and jurors are restricted exclusively to admitted, non-struck testimony.
- **Hybrid Statutory Retrieval (RAG)**: Reciprocal Rank Fusion (RRF, $k=60$) combining exact statutory section lookups, PostgreSQL weighted full-text search (`tsvector`), and 1024-dimensional dense vector embeddings with role-based audience filtering.
- **Interactive Human Modes**: Step in and play as **Counsel** (examine witnesses, object with shortcut `O`), **Presiding Judge** (rule on objections, pronounce judicial decrees), or **Juror** (cast secret ballots and argue in deliberations).
- **Procedural 3D Courtroom & Audio**: Real-time React Three Fiber courtroom chamber, procedural Web Audio API gavel and ambient effects, browser-native Text-to-Speech (TTS) with Indian English role acoustic profiles, and interactive trial replay.
- **Evaluation & Bias Auditing**: Headless batch evaluation runner (`scripts/run_batch.py`), 95% Wilson score confidence interval truth-matching reports (`scripts/report.py`), and demographic bias auditing laboratory (`scripts/bias_lab.py`).

---

## ⚖️ Statutory Foundations & Jurisprudence

The system natively operates on official statutory enactments codified under Acts of the Indian Parliament:
- **Bharatiya Nyaya Sanhita, 2023 (Act No. 45 of 2023)**: Penal offenses (e.g. BNS 103(1) Murder, BNS 318(4) Cheating, BNS 117(2) Grievous Hurt).
- **Bharatiya Nagarik Suraksha Sanhita, 2023 (Act No. 46 of 2023)**: Criminal procedure, trial stages, and sessions cognizance.
- **Bharatiya Sakshya Adhiniyam, 2023 (Act No. 47 of 2023)**: Evidentiary admissibility, electronic records, hearsay exclusions, and burden of proof.
- **Constitution of India**: Articles 20, 21, 22 (Fair trial & Golden Triangle) and Article 141 (Binding Supreme Court precedents).

---

## 🏗️ Architecture & Technology Stack

```
 court simulator/
 ├── backend/                   # FastAPI async application
 │   ├── app/
 │   │   ├── api/v1/            # REST endpoints (auth, cases, trials, admin)
 │   │   ├── context/           # Role-based context boundary filters
 │   │   ├── db/models/         # SQLAlchemy 2.0 ORM models
 │   │   ├── llm/               # Provider failover router & key cooldown pools
 │   │   ├── orchestrator/      # LangGraph state graph & human action gates
 │   │   ├── rag/               # Hybrid RRF retriever, chunker & citation verifier
 │   │   ├── rules/             # Pure statutory admissibility & objection logic
 │   │   ├── verdict/           # Textualist, Precedent & Fairness jurisprudence
 │   │   └── voting/            # 0.5*J + 0.5*P hybrid scoring & hung bands
 │   └── tests/                 # Unit, isolation, and integration suites
 ├── frontend/                  # React 19 + TypeScript + Vite 6
 │   ├── src/
 │   │   ├── audio/             # Procedural Web Audio SFX & Web Speech TTS
 │   │   ├── camera/            # Cinema director camera shot transitions
 │   │   ├── characters/        # Rigged 3D procedural humanoid characters
 │   │   ├── scene/             # React Three Fiber courtroom chamber
 │   │   ├── store/             # Zustand trial state & event queue
 │   │   └── ui/                # LawyerPanel, JudgePanel, JurorPanel, Replay
 └── scripts/                   # Ingestion, batch runner, bias lab & reports
```

### Core Technologies
- **Backend**: Python 3.12+, FastAPI, LangGraph, SQLAlchemy 2.0, Alembic, Pydantic v2, PostgreSQL 17 + pgvector.
- **LLM Routing**: KeyPool with exponential backoff failover supporting Gemini, Groq, OpenRouter, and Ollama.
- **Frontend**: React 19, TypeScript strict mode, Vite 6, Tailwind CSS 4, Zustand 5, Three.js, React Three Fiber.
- **Audio**: Web Audio API (procedural gavel transient & resonance synthesis) + Web Speech API (per-role speech synthesis).

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- **Python**: 3.12 or newer
- **Node.js**: 22 LTS or newer (`pnpm` or `npm`)
- **Database**: PostgreSQL 17+ with the `pgvector` extension enabled

### 2. Environment Configuration
Copy `.env.example` to `.env` and configure your credentials:
```bash
cp .env.example .env
```
Ensure your database connection string and LLM provider keys (Gemini, Groq, OpenRouter) are set in `.env`.

### 3. Backend Setup
```bash
# Navigate to backend and install dependencies
pip install -r backend/requirements.txt

# Run database migrations
cd backend
alembic upgrade head
cd ..

# Load sample statutory cases
python scripts/load_cases.py
```

### 4. Frontend Setup
```bash
# Navigate to frontend and install dependencies
cd frontend
npm install
cd ..
```

### 5. Running the Application
In terminal 1 (Backend API):
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

In terminal 2 (Frontend Client):
```bash
cd frontend
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your web browser.

---

## 🎮 Courtroom Modes

| Mode | Role | Description |
|---|---|---|
| **Spectator** | Observer | Full automated trial with camera direction, live captions, and optional voice dialogue. |
| **Human Lawyer** | Prosecutor / Defense | Type examination questions, introduce evidence, and raise objections (Hotkey: `O`). |
| **Presiding Judge** | Sessions Judge | Adjudicate objections (`Sustain` / `Overrule`) and pronounce final judicial verdicts. |
| **Citizen Juror** | Empaneled Juror | Cast secret pre- and post-deliberation ballots and debate guilt probabilities. |
| **Trial Replay** | Reviewer | Stream historical trial events via SSE with transport controls and speed multipliers. |

---

## 🧪 Testing & Verification

The test suite enforces rigorous quality and context isolation standards:

```bash
# Backend unit & isolation test suite (225 tests)
python -m pytest backend/tests/ -v

# Frontend component & audio test suite (53 tests)
cd frontend && npm test -- --run

# TypeScript typecheck
cd frontend && npx tsc -b

# ESLint check
cd frontend && npm run lint

# Python Ruff formatting & lint check
python -m ruff check --config backend/pyproject.toml backend/ scripts/

# Python Mypy strict typecheck
python -m mypy backend/app/
```

---

## 📊 Evaluation & Research CLI

### Unattended Headless Batch Runner
Run multiple trials sequentially without browser UI to evaluate truth-match rates:
```bash
python scripts/run_batch.py --case case_001 --runs 5 --jurors 7 --rounds 2 --fake-llm
```

### Metrics & Context Isolation Audit
Generate statistical reports with 95% Wilson score confidence intervals and citation integrity checks:
```bash
python scripts/report.py --input data/eval/runs/run_state-v-k-sharma-2024.jsonl --output data/eval/reports/report.json
```

### Demographic Neutrality & Bias Laboratory
Test deliberation consistency across diverse cognitive panels without demographic attributes:
```bash
python scripts/bias_lab.py --case case_001 --runs-per-panel 3 --fake-llm
```

---

## 📜 Ethical AI Charter & Legal Notice

### Educational & Research Scope
Verdict is an autonomous computational research system created for evaluating multi-agent decision dynamics and legal knowledge retrieval. It is **not legal advice** and does not substitute for licensed legal representation.

### Demographic Neutrality
In accordance with the project's ethical charter:
- **Zero Demographic Persona Attributes**: Jurors are never parameterized by religion, caste, gender, ethnicity, community, or socioeconomic identity.
- **Epistemological Profiling**: Deliberation variations are driven solely by cognitive reasoning styles (analytical, holistic, doctrinal, evidentiary).

### Statutory License Notice
Statutory enactments of the Bharatiya Nyaya Sanhita, Bharatiya Nagarik Suraksha Sanhita, Bharatiya Sakshya Adhiniyam, and Constitution of India are reproduced under **Section 52(1)(q) of the Indian Copyright Act, 1957** (acts permitted without infringement: reproduction of any Act of a Legislature or judicial proceedings).

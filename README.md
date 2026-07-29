"""
# OpsFlow AI

**AI-first Operations Automation Platform** for enterprise knowledge retrieval, task automation, meeting intelligence, and workflow orchestration.

Built as a portfolio-quality system for AI Innovation Engineer / AI Operations roles — combining **RAG**, **multi-agent orchestration (LangChain / LangGraph)**, **FastAPI**, **Streamlit**, and **n8n**.

---

## Features

| Capability | Description |
|---|---|
| **Knowledge Agent (RAG)** | Ask questions over company PDFs/DOCX/TXT with citations + confidence scores |
| **Task Agent** | Convert natural language into structured tasks (title, priority, owner, deadline) |
| **Meeting Agent** | Summarise transcripts → decisions + action items → auto-created tasks |
| **Reporting Agent** | Weekly operational reports with bottlenecks and trends |
| **Employee Onboarding** | New hire → welcome email → n8n accounts checklist → HR tasks → Slack |
| **Conversation history** | Persisted chats with agent metadata and citations |
| **Analytics** | Queries solved, estimated hours saved, common request types |
| **n8n automation** | Email → task, document indexed → notify, meeting → Slack/email |

---

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────────┐
│  Streamlit UI   │────►│  FastAPI Backend     │────►│  AI Agents              │
│  (6 pages)      │     │  /api/v1/*           │     │  Knowledge | Task       │
└─────────────────┘     │                      │     │  Meeting  | Reporting  │
                        │  SQLite / Postgres   │     └───────────┬─────────────┘
                        │  ChromaDB vectors    │                 │
                        └──────────┬───────────┘                 │
                                   │                             │
                                   ▼                             ▼
                        ┌──────────────────────┐     ┌─────────────────────────┐
                        │  n8n Workflows       │     │  OpenAI + Sentence      │
                        │  Slack / Email hooks │     │  Transformers embeddings│
                        └──────────────────────┘     └─────────────────────────┘
```

### AI workflow (Knowledge Agent)

1. User question enters the orchestrator  
2. Intent routed to **Knowledge Agent**  
3. Query embedded → top-k chunks retrieved from Chroma  
4. Chunks filtered by similarity threshold  
5. LLM answers grounded only in retrieved context  
6. Confidence score computed from retrieval quality + grounding  
7. Citations returned to the UI  

---

## Project structure

```
├── frontend/
│   └── streamlit_app.py          # Operations dashboard
├── backend/
│   ├── main.py                   # FastAPI entrypoint
│   ├── api/                      # REST routers
│   ├── agents/                   # Knowledge, Task, Meeting, Reporting, Orchestrator
│   ├── rag/                      # Loaders, chunking, vector store, pipeline
│   ├── database/                 # SQLAlchemy session
│   ├── models/                   # ORM + Pydantic schemas
│   ├── services/                 # Business logic + n8n hooks
│   └── core/                     # Config, security, deps
├── automation/n8n_workflows/     # Importable n8n JSON workflows
├── documents/                    # Uploaded company docs (+ sample policy)
├── tests/                        # Pytest suite
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

---

## Quick start (local)

### 1. Prerequisites

- Python 3.11+
- OpenAI API key (optional for offline demos — heuristic agents still work)

### 2. Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
```

Edit `.env` and set:

```
OPENAI_API_KEY=sk-...
```

### 3. Run backend

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Run frontend

```bash
streamlit run frontend/streamlit_app.py
```

UI: [http://localhost:8501](http://localhost:8501)

Default login: `admin` / `opsflow-admin-change-me`

### 5. Try the sample policy

1. Open **Document Upload**  
2. Upload `documents/sample_ops_policy.txt`  
3. Ask in chat: *“How quickly must production incidents be acknowledged?”*  
4. Inspect citations + confidence score  

---

## Docker

```bash
copy .env.example .env
docker compose up --build
```

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| Streamlit UI | http://localhost:8501 |
| n8n | http://localhost:5678 |

Import workflows from `automation/n8n_workflows/` into n8n.

---

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/auth/login` | JWT login |
| `POST` | `/api/v1/chat` | Orchestrated Operations AI chat |
| `POST` | `/api/v1/documents/upload` | Upload + RAG index |
| `GET/POST/PATCH` | `/api/v1/tasks` | Task management |
| `POST` | `/api/v1/tasks/extract` | NL → tasks |
| `POST` | `/api/v1/meetings/summarise` | Meeting intelligence |
| `POST` | `/api/v1/reports/generate` | Weekly ops report |
| `GET` | `/api/v1/analytics` | KPI dashboard data |
| `GET` | `/api/v1/health` | Health check |

---

## Security

- Secrets via environment variables (never hardcoded)
- JWT bearer authentication (`python-jose` + `passlib` bcrypt)
- Upload validation (extension allow-list, size limit, safe filenames)
- Pydantic request validation on all write endpoints
- Automation webhook failures are non-blocking

---

## Testing

```bash
pytest -q
```

Tests cover:

- Auth, tasks, document upload + RAG chat  
- Meeting summarisation + report generation  
- Intent classification and offline agent heuristics  
- Chunking / retrieval confidence  

---

## n8n example flows

See [`automation/n8n_workflows/README.md`](automation/n8n_workflows/README.md).

- **Email → OpsFlow → Task → Slack**  
- **Document upload → Vector DB update → Email/Slack**  
- **Meeting summary → Slack + Email**  

---

## Design notes for interviewers

- **Modular agents** keep RAG, task extraction, meetings, and reporting independently testable  
- **Offline fallbacks** demonstrate graceful degradation without an LLM key  
- **Confidence + citations** make RAG answers auditable for operations teams  
- **n8n hooks** show how AI decisions plug into real enterprise automation  

---

## License

MIT — built for educational / portfolio demonstration purposes.

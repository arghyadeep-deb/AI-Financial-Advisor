# AI Financial Advisor

![Frontend](https://img.shields.io/badge/Frontend-HTML%20%7C%20CSS%20%7C%20JS-success)
[![Backend](https://img.shields.io/badge/Backend-Render-blue?logo=render)](https://ai-financial-advisor-1-fac2.onrender.com)
[![API Docs](https://img.shields.io/badge/API-Docs-orange?logo=fastapi)](https://ai-financial-advisor-1-fac2.onrender.com/docs)
[![Health](https://img.shields.io/badge/Health-Check-brightgreen)](https://ai-financial-advisor-1-fac2.onrender.com/health)

An agent-driven, modular AI financial advisory platform built with a FastAPI backend, persistent storage, and extensible intelligence layers for personalized analysis, recommendations, simulation, and conversational guidance.

---

## About the Project

**AI Financial Advisor** is designed to deliver practical, explainable, and personalized financial assistance through:

- Financial profile analysis and health checks  
- Credit-oriented guidance  
- Investment and portfolio rebalancing support  
- Optimization and what-if simulation workflows  
- Chat-based advisor interactions with thread continuity
  

The codebase follows a layered architecture with clear separation of concerns:
- **Controllers** for API routing
- **Services** for business logic
- **Schemas** for request/response contracts
- **Models/DB** for persistence
- **Agents** for specialized financial intelligence

---

## Key Features

- Multi-agent financial reasoning architecture  
- FastAPI backend with modular controller structure  
- Auth, profile, chat, analysis, and thread API domains  
- Financial simulation + optimization pathways  
- Portfolio rebalance and summary generation agents  
- Local persistence via SQLite (`advisor.db`)  
- Utility workflows for data conversion and graph rebuild  
- Extensible modules for RAG, memory, tools, and intelligence

---

## Live Deployment Links

### Frontend (plain HTML/CSS/JS)
- Lives in `frontend/static/` and is served by the API itself at `/app` (no build step, no separate frontend server).
- The old hosted Streamlit app was replaced; it is no longer maintained.

### Backend (Render Deployment)
- **Base API URL:** https://ai-financial-advisor-1-fac2.onrender.com  
- This is the production backend host used by frontend/API clients.

### Open the web app
Start the API (`uvicorn backend.main:app`) and open `http://127.0.0.1:8000/app/`. The login token is kept in memory only, so a page reload asks you to log in again.

Browser tests: `pip install -r requirements-dev.txt && python -m playwright install chromium && python -m pytest tests/web -q`.

### Database migrations
The schema is managed by Alembic (`alembic.ini`, `migrations/`). The API checks or applies migrations at startup
(`AUTO_MIGRATE`). Existing pre-Alembic databases are backed up (SQLite) and stamped automatically; see
`specs/implementation-handoff.md` for the backup, restore and rollback steps.
```bash
python -m backend.core.migrations_runner --help
```

### Run the tests
```bash
python -m pytest tests -q
```
Uses isolated temporary databases and mocked providers - no network, no real keys. PostgreSQL tests run only when
`TEST_POSTGRES_URL` is set.

### API Documentation (Swagger)
- **URL:** https://ai-financial-advisor-1-fac2.onrender.com/docs  
- Use this to explore and test all available API endpoints interactively.

### Health Check Endpoint
- **URL:** https://ai-financial-advisor-1-fac2.onrender.com/health  
- Use this to verify backend service status and availability.

---

## Quick Start for Users (Hosted Version)

If you only want to use the deployed app (no local setup):

1. Open the web app at `<backend URL>/app/`.

2. If frontend appears slow on first load, wait a few seconds (Render free-tier cold starts may occur).

3. Verify backend status (optional):  
   https://ai-financial-advisor-1-fac2.onrender.com/health

4. Explore APIs directly (for developers):  
   https://ai-financial-advisor-1-fac2.onrender.com/docs

---

## Architecture Flow

```text
Client/UI
   │
   ▼
FastAPI App (backend/main.py)
   │
   ▼
Controllers (auth/analysis/chat/profile/thread)
   │
   ▼
Services (business logic orchestration)
   │
   ├── Agents (credit, health, investment, rebalance, simulation, summary)
   ├── Intelligence/Engines
   ├── RAG + Knowledge Base
   ├── Memory
   └── Database Repository
          │
          ▼
       advisor.db
```

---

## Tech Stack

- **Language:** Python  
- **Backend Framework:** FastAPI  
- **ASGI Server:** Uvicorn  
- **Validation:** Pydantic schemas  
- **Database:** SQLite  
- **Architecture:** Layered API + Agentic Intelligence  
- **Dependency Management:** `backend_requirements.txt`, `requirements-dev.txt`  
- **Deployment:** Render (API + static web app)

---

## Project Structure

```bash
AI-Financial-Advisor/
├── .cache/
├── .env
├── .gitignore
├── advisor.db
├── backend_requirements.txt
├── convert_data_sources.py
├── rebuild_graph.py
│
├── agents/
│   ├── __init__.py
│   ├── credit_agent.py
│   ├── graph_executor.py
│   ├── health_agent.py
│   ├── investment_agent.py
│   ├── optimizer_agent.py
│   ├── rebalance_agent.py
│   ├── simulation_agent.py
│   └── summary_agent.py
│
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── auth_controller.py
│   │   ├── analysis_controller.py
│   │   ├── chat_controller.py
│   │   ├── profile_controller.py
│   │   └── thread_controller.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── dependencies.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py
│   └── services/
│       ├── __init__.py
│       ├── analysis_service.py
│       ├── auth_service.py
│       ├── chat_service.py
│       └── profile_service.py
│
├── database/
│   ├── __init__.py
│   └── repository.py
│
├── data_sources/
├── engines/
├── frontend/
├── intelligence/
├── knowledge_base/
├── mcp_tools/
├── memory/
├── rag/
├── utils/
└── .venv/
```

---

## Module Responsibilities

### `backend/controllers/`
Route-layer API handlers:
- `auth_controller.py` – authentication endpoints  
- `analysis_controller.py` – financial analysis endpoints  
- `chat_controller.py` – conversational advisor endpoints  
- `profile_controller.py` – profile-related endpoints  
- `thread_controller.py` – thread/session endpoints  
- `main.py` – controller router aggregation  

### `backend/services/`
Business logic per domain:
- `auth_service.py`
- `analysis_service.py`
- `chat_service.py`
- `profile_service.py`

### `agents/`
Specialized financial reasoning modules:
- `credit_agent.py`
- `health_agent.py`
- `investment_agent.py`
- `optimizer_agent.py`
- `rebalance_agent.py`
- `simulation_agent.py`
- `summary_agent.py`
- `graph_executor.py` (agent orchestration flow)

### `backend/core/`
Core infra: auth, config, database setup, and shared dependencies.

### `backend/schemas/`
Pydantic request/response schemas for API consistency.

### `database/repository.py`
Database access abstraction (repository pattern).

---

## Setup & Installation (Local Development)

### 1) Clone the repository
```bash
git clone https://github.com/arghyadeep-deb/AI-Financial-Advisor.git
cd AI-Financial-Advisor
```

### 2) Create and activate virtual environment

#### macOS/Linux
```bash
python -m venv .venv
source .venv/bin/activate
```

#### Windows (PowerShell)
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3) Install dependencies
```bash
pip install -r requirements-dev.txt   # backend + frontend + test tools
```

### 4) Configure environment variables
Copy `.env.example` to `.env`. Outside `APP_ENV=development` a strong `SECRET_KEY` is mandatory
(the app refuses to start with a weak key, wildcard CORS, or SQLite). With no model keys the app still runs and
returns clearly labelled deterministic fallbacks.

---

## Running the Application Locally

### Start backend
```bash
uvicorn backend.main:app --reload
```

### API Documentation
- Swagger: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

> The web UI is in `frontend/static/` and is served at `/app/`.

---

## Utility Scripts

### Convert/normalize data sources
```bash
python convert_data_sources.py
```

### Rebuild graph/index structures
```bash
python rebuild_graph.py
```

---

## API Domains (by controller structure)

- **Auth** (`auth_controller.py`)
- **Analysis** (`analysis_controller.py`)
- **Chat** (`chat_controller.py`)
- **Profile** (`profile_controller.py`)
- **Thread** (`thread_controller.py`)

For exact paths and payloads, check route decorators and schemas in:
- `backend/controllers/*.py`
- `backend/schemas/schemas.py`

---

## Deployment Notes for Users & Developers

- The web app is served by the backend at `/app/`.

- Use the **hosted backend** for programmatic/API access:
  - https://ai-financial-advisor-1-fac2.onrender.com

- Use **Swagger docs** to test endpoints:
  - https://ai-financial-advisor-1-fac2.onrender.com/docs

- Use **health endpoint** for uptime checks/monitoring:
  - https://ai-financial-advisor-1-fac2.onrender.com/health

- If requests are initially slow, retry after a short wait due to cold starts on free hosting tiers.

---

## Security & Privacy Notes

- Never commit secrets from `.env`  
- Protect local DB (`advisor.db`) and sensitive user finance data  
- Enforce auth checks on private/profile routes  
- Avoid logging raw personally identifiable financial data  
- Add secure deployment controls for production environments

---

## Contributing

1. Fork the repository  
2. Create a feature branch  
3. Implement changes with clear modular boundaries  
4. Add/update tests and docs  
5. Open a Pull Request with summary and rationale  
---

## 🗺️ Roadmap

- [x] Core platform live (FastAPI backend, HTML/CSS/JS web app, multi-agent architecture)
- [ ] Better API docs with clear request/response examples
- [ ] Enhanced explainability for every recommendation
- [ ] Smarter personalization using memory + thread context
- [ ] Testing + CI/CD for production reliability
- [ ] Portfolio analytics, simulations, and exportable reports


# AI-First CRM — Intelligent HCP Interaction Manager

An AI-first Customer Relationship Management (CRM) system for pharmaceutical field representatives to log Healthcare Professional (HCP) interactions via conversational AI. The React form is **read-only** — only the LangGraph AI agent updates it.

## Architecture

```
User → React Chat → FastAPI /chat → LangGraph Agent → Groq LLM
                                          ↓
                                    Tool Selection
                                          ↓
                                      Database
                                          ↓
                                    Redux State → React Form
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Redux Toolkit, Vite |
| Backend | Python, FastAPI |
| AI Agent | LangGraph |
| LLM | Groq — `llama-3.3-70b-versatile` (assignment-approved; `gemma2-9b-it` decommissioned by Groq) |
| Database | **PostgreSQL** (via Docker Compose) |
| Font | Google Inter |

## LangGraph Agent & 5 Tools

The LangGraph agent is the core product. It receives chat messages, detects intent via LLM, selects a tool, executes it, updates the database, and returns the updated interaction form.

| # | Tool | Description |
|---|------|-------------|
| 1 | **Log Interaction** *(required)* | Extracts doctor, date, products, sentiment, brochure/samples from natural language. Asks for missing info and confirms before saving. |
| 2 | **Edit Interaction** *(required)* | Modifies specific fields in the current interaction (e.g. "Change sentiment to negative"). |
| 3 | **Search Interaction** | Finds past meetings by doctor name and loads them into the form. |
| 4 | **Summarize Interaction** | Generates a concise professional summary of a visit. |
| 5 | **Schedule Follow-up** | Sets follow-up date, status, and reminder notes. |

### Bonus AI Behaviors

- **Ask for missing information** — "I met a doctor today" → AI asks for the doctor's name
- **Confirmation before saving** — Shows extracted fields and asks "Should I save this?"
- **Undo last edit** — "Undo the previous change" reverts the form
- **Conversation memory** — Session-based context for follow-up messages
- **Field validation** — Prevents empty doctor names, invalid dates, invalid sentiment values

## Project Structure

```
├── frontend/
│   ├── src/
│   │   ├── components/   # ChatPanel, FormPanel
│   │   ├── store/        # Redux (interactionSlice)
│   │   └── services/     # API client
│   └── package.json
├── backend/
│   ├── agent/
│   │   ├── graph.py      # LangGraph workflow
│   │   ├── tools.py      # 5 agent tools
│   │   ├── prompts.py    # LLM prompts per tool
│   │   └── state.py      # Agent state schema
│   ├── main.py           # FastAPI entry point
│   ├── routes.py         # /chat + /interaction CRUD
│   ├── models.py         # SQLAlchemy Interaction model
│   └── database.py
├── docker-compose.yml    # PostgreSQL
└── README.md
```

## Prerequisites

- **Node.js** 18+
- **Python** 3.11+
- **Groq API key** — [console.groq.com](https://console.groq.com/)
- **Docker Desktop** — required for PostgreSQL (assignment requirement)

## Quick Start

### 1. Clone & configure

```bash
cd "AI-First CRM Intelligent HCP Interaction Manager"
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set your Groq API key:

```
GROQ_API_KEY=gsk_your_key_here
DATABASE_URL=postgresql://hcp_user:hcp_password@localhost:5433/hcp_crm
GROQ_MODEL=llama-3.3-70b-versatile  # assignment-approved alternative to gemma2-9b-it
```

> **Note on LLM model:** The assignment specifies `gemma2-9b-it` or `llama-3.3-70b-versatile`. Groq decommissioned `gemma2-9b-it` in October 2025, so this project uses `llama-3.3-70b-versatile`, which the assignment explicitly allows.

### 2. Start PostgreSQL (dedicated container for this project)

This project uses its **own** PostgreSQL container — it does **not** use any existing Postgres on your machine.

| Setting | Value |
|---------|-------|
| Container name | `hcp_crm_postgres` |
| Host port | **5433** (avoids conflict with default Postgres on 5432) |
| Database | `hcp_crm` |
| User / Password | `hcp_user` / `hcp_password` |

Open **Docker Desktop**, then run:

```bash
docker compose up -d
```

Wait until the database is healthy:

```bash
docker compose ps
```

### 3. Start the backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Start the frontend

Create `frontend/.env` so the frontend calls the backend directly:

```
VITE_API_BASE=http://127.0.0.1:8000/api
```

Then install and run:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Main endpoint — frontend sends chat messages here |
| `POST` | `/api/interaction` | Create interaction (internal/CRUD) |
| `GET` | `/api/interaction` | List interactions |
| `GET` | `/api/interaction/{id}` | Get interaction by ID |
| `PUT` | `/api/interaction/{id}` | Update interaction |
| `DELETE` | `/api/interaction/{id}` | Delete interaction |
| `GET` | `/api/health` | Health check |

## Demo Commands

Try these in the chat panel:

```
Today I met Dr. Smith. We discussed Product X. He liked it. Shared brochures.
```

```
Sorry, sentiment should be negative.
```

```
Show my last meeting with Dr. Smith.
```

```
Summarize today's visit.
```

```
Schedule follow-up next Monday.
```

```
Undo the previous change.
```

## Video Demo Checklist

For your 10–15 minute submission video, demonstrate:

1. Frontend walkthrough (split screen: read-only form + chat)
2. All 5 LangGraph tools working
3. Confirmation flow (log → confirm → save)
4. Code structure overview (`agent/graph.py`, `tools.py`, Redux store)
5. Brief summary of the task understanding

## License

Built for the Naukri APR Round 1 technical assignment.

# AI-First CRM — Intelligent HCP Interaction Manager

An AI-first Customer Relationship Management (CRM) system for pharmaceutical field representatives to log Healthcare Professional (HCP) interactions. The **Log HCP Interaction** screen combines a structured read-only form with a conversational AI assistant — the LangGraph agent is the core product; the form is the display layer.

## Assignment Overview

Built for the **Naukri APR Round 1** technical assignment: *AI-First CRM HCP Module — Log Interaction Screen*.

| Requirement | Implementation |
|-------------|----------------|
| Log Interaction Screen | Split UI: structured form (left) + chat (right) |
| Form **or** chat logging | Chat drives the form; form is AI-controlled (read-only) |
| React + Redux | React 18, Redux Toolkit, Vite |
| FastAPI backend | Python FastAPI on port 8000 |
| LangGraph agent | **Mandatory** — `backend/agent/graph.py` |
| Groq LLM | `llama-3.3-70b-versatile` *(assignment-approved; gemma2-9b-it decommissioned)* |
| PostgreSQL | Docker Compose, dedicated container on port **5433** |
| Google Inter font | Loaded in `frontend/index.html` |
---



## Demo Video

https://github.com/user-attachments/assets/0156b2cf-2de1-40b8-8db1-3ec37dc78e6f


## Architecture

```
User types in AI Assistant chat
        ↓
React (Redux) → POST /api/chat
        ↓
FastAPI → LangGraph Agent
        ↓
Groq LLM → Intent Detection → Tool Selection
        ↓
Execute Tool → PostgreSQL
        ↓
Return { reply, interaction } → Redux → Form updates
```

### LangGraph Agent Role

The LangGraph agent **manages all HCP interactions**. It:

1. Receives natural-language messages from the field rep
2. Classifies intent (log, edit, search, summarize, schedule, confirm)
3. Selects and executes the correct tool
4. Uses the LLM to extract structured data from conversation
5. Reads/writes PostgreSQL
6. Returns updated interaction JSON so the React form stays in sync

The frontend **only** calls `/api/chat`. All business logic runs inside the agent.

## UI — Log HCP Interaction Screen

**Left panel — Interaction Details (read-only, AI-filled):**

| Field | Description |
|-------|-------------|
| HCP Name | Doctor / healthcare professional |
| Interaction Type | Meeting, Call, Email, etc. |
| Date & Time | Auto-fills today + current time on new logs |
| Attendees | Other people present |
| Topics Discussed | Key discussion points |
| Materials Shared / Samples | Brochures, PDFs, samples |
| HCP Sentiment | Positive / Neutral / Negative |
| Outcomes | Agreements and results |
| Follow-up Actions | Next steps and tasks |
| AI Suggested Follow-ups | Clickable suggestions → sent to chat |

**Right panel — AI Assistant:**

- Chat interface with **Log** button
- All 5 LangGraph tools accessible via natural language

## LangGraph — 5 Tools

| # | Tool | Example command |
|---|------|--------------------|
| 1 | **Log Interaction** | *"Today I met Dr. Smith. Discussed Product X. Positive sentiment. Shared brochures."* |
| 2 | **Edit Interaction** | *"Change sentiment to negative"* |
| 3 | **Search Interaction** | *"Show my last meeting with Dr. Smith"* |
| 4 | **Summarize Interaction** | *"Summarize today's visit"* |
| 5 | **Schedule Follow-up** | *"Next meeting is tomorrow"* |

### Bonus AI Behaviors

- Asks for missing information (e.g. doctor name)
- Confirmation before saving — type **`yes`** or **`save to database`**
- Edit then save — form is always the source of truth on save
- Undo last edit
- Session conversation memory
- Field validation (doctor name, dates, sentiment)
- Auto-fills today's date, topics/notes, and follow-up dates ("tomorrow", "next Monday")

## Project Structure

```
AI-First CRM Intelligent HCP Interaction Manager/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FormPanel.jsx      # Log HCP Interaction form
│   │   │   └── ChatPanel.jsx      # AI Assistant sidebar
│   │   ├── store/
│   │   │   ├── interactionSlice.js  # Redux state
│   │   │   └── store.js
│   │   └── services/api.js        # POST /api/chat
│   ├── .env.example
│   └── package.json
├── backend/
│   ├── agent/
│   │   ├── graph.py               # LangGraph workflow
│   │   ├── tools.py               # 5 agent tools
│   │   ├── prompts.py             # LLM prompts
│   │   └── state.py               # Agent state schema
│   ├── main.py                    # FastAPI entry
│   ├── routes.py                  # /chat + CRUD APIs
│   ├── models.py                  # PostgreSQL Interaction model
│   ├── database.py                # DB + auto-migration
│   └── requirements.txt
├── docker-compose.yml             # PostgreSQL (port 5433)
├── start.bat                      # Windows one-click launcher
└── README.md
```

## Prerequisites

- **Node.js** 18+
- **Python** 3.11+
- **Docker Desktop** (for PostgreSQL)
- **Groq API key** — [console.groq.com](https://console.groq.com/)

## Quick Start

### 1. Configure environment

```bash
cd "AI-First CRM Intelligent HCP Interaction Manager"
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit `backend/.env`:

```
GROQ_API_KEY=gsk_your_key_here
DATABASE_URL=postgresql://hcp_user:hcp_password@localhost:5433/hcp_crm
GROQ_MODEL=llama-3.3-70b-versatile
```

> **LLM note:** Assignment lists `gemma2-9b-it` or `llama-3.3-70b-versatile`. Groq decommissioned `gemma2-9b-it`; this project uses the assignment-approved alternative.

### 2. Start PostgreSQL

Open **Docker Desktop**, then from the **project root**:

```bash
docker compose up -d
docker compose ps    # wait until healthy
```

| Setting | Value |
|---------|-------|
| Container | `hcp_crm_postgres` |
| Port | **5433** (not 5432 — avoids conflicts) |
| Database | `hcp_crm` |
| User / Password | `hcp_user` / `hcp_password` |

### 3. Start backend

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

Verify: http://127.0.0.1:8000/api/health

### 4. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

### Windows shortcut

Double-click `start.bat` in the project root (starts Docker, backend, frontend).

## How to Use

### Log a new visit

1. Type in chat:
   ```
   Today I met Dr. Yashi. Discussed thyroid medicine. Positive sentiment. Shared brochures.
   ```
2. Form fills automatically (draft — not saved yet)
3. Type **`yes`** or **`save to database`** to save to PostgreSQL
4. Form shows **Saved #ID**

### Edit, search, summarize, schedule

```
Change sentiment to negative
Show my last meeting with Yashi
Summarize today's visit
Next meeting is tomorrow
```

### Important rules

| Rule | Why |
|------|-----|
| Always type **yes** / **save** after logging | Data is not in DB until confirmed |
| Search using the **same doctor name** you saved | Search matches by HCP name |
| Form is read-only | AI-first design — agent controls all fields |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | **Main endpoint** — frontend chat |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/interaction` | Create interaction (CRUD) |
| `GET` | `/api/interaction` | List all interactions |
| `GET` | `/api/interaction/{id}` | Get by ID |
| `PUT` | `/api/interaction/{id}` | Update by ID |
| `DELETE` | `/api/interaction/{id}` | Delete by ID |




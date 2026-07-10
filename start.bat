@echo off
echo Starting AI-First CRM HCP Interaction Manager...
echo.

echo [1/3] Starting PostgreSQL (Docker)...
docker compose up -d
if errorlevel 1 (
    echo.
    echo ERROR: Could not start PostgreSQL. Make sure Docker Desktop is running!
    echo Open Docker Desktop, wait for it to start, then run this script again.
    pause
    exit /b 1
)

timeout /t 5 /nobreak >nul

echo [2/3] Starting Backend...
start "HCP CRM Backend" cmd /k "cd /d %~dp0backend && python -m venv venv 2>nul && call venv\Scripts\activate && pip install -r requirements.txt -q && uvicorn main:app --reload --port 8000"

timeout /t 3 /nobreak >nul

echo [3/3] Starting Frontend...
start "HCP CRM Frontend" cmd /k "cd /d %~dp0frontend && npm install && npm run dev"

echo.
echo PostgreSQL: localhost:5433  (dedicated container: hcp_crm_postgres)
echo Backend:    http://localhost:8000
echo Frontend:   http://localhost:5173
echo.
echo Make sure backend/.env has your GROQ_API_KEY set!
pause

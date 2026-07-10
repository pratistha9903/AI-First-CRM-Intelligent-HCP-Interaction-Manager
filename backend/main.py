from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from config import settings
from database import init_db
from routes import router

app = FastAPI(
    title="AI-First CRM — HCP Interaction Manager",
    description="LangGraph-powered CRM for Healthcare Professional interactions",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model": settings.groq_model,
        "database": "connected",
    }

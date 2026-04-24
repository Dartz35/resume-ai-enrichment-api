"""
Resume AI Enrichment API — entry point.

Wires together:
  - FastAPI application + CORS
  - /health  (no auth, no rate limit)
  - /resume/* (rate-limited, optional API-key auth)

Run locally:
  uvicorn main:app --reload

Run via Docker:
  docker build -t resume-ai-api .
  docker run -p 8000:8000 -e ANTHROPIC_API_KEY=sk-ant-... resume-ai-api
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.health import router as health_router
from routes.resume import router as resume_router

# ---------------------------------------------------------------------------
# Lifespan (replaces deprecated @app.on_event)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError(
            "GEMINI_API_KEY environment variable is not set. "
            "Set it before starting the server."
        )
    yield


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Resume AI Enrichment API",
    description=(
        "Parse resumes, score candidates against job descriptions, "
        "rewrite bullet points, and surface trending skills — all powered by Claude."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# Wide-open CORS is appropriate for a public API published on RapidAPI.
# Tighten allow_origins if you serve a private deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # credentials=True is incompatible with allow_origins=["*"]
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health_router)
app.include_router(resume_router, prefix="/resume")

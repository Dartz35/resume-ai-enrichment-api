"""
Shared fixtures for the Resume AI Enrichment API test suite.

Key decisions:
  - ANTHROPIC_API_KEY is set before main.py is imported so the startup guard passes.
  - The rate limiter store is cleared before every test so quota checks start fresh.
  - `client` is function-scoped (each test gets a clean TestClient + lifespan cycle).
  - `claude_parse_response`, `claude_score_response`, etc. are canonical dicts that
    mirror what a real Claude call would return; individual tests can override fields.
"""

from __future__ import annotations

import os

# Must be set before main is imported so the startup guard passes.
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key-for-pytest")

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    from main import app as _app
    return _app


@pytest.fixture
def client(app):
    """Fresh TestClient per test (triggers ASGI lifespan startup/shutdown)."""
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Rate limiter reset
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Wipe the in-memory rate limit counters before and after every test."""
    from services.rate_limiter import rate_limiter
    rate_limiter._store.clear()
    yield
    rate_limiter._store.clear()


# ---------------------------------------------------------------------------
# Canonical Claude response payloads
# ---------------------------------------------------------------------------

@pytest.fixture
def parse_payload():
    return {
        "name": "Alice Smith",
        "email": "alice@example.com",
        "phone": "+1-555-0100",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "experience_years": 5.0,
        "experience": [
            {
                "company": "Acme Corp",
                "title": "Senior Engineer",
                "duration": "2019-2024",
                "description": "Built REST APIs serving 50K daily requests.",
            }
        ],
        "education": [
            {
                "institution": "McGill University",
                "degree": "B.Sc.",
                "field": "Computer Science",
                "year": "2019",
            }
        ],
        "languages": ["English", "French"],
    }


@pytest.fixture
def score_payload():
    return {
        "overall_score": 82,
        "skill_match": 85,
        "experience_match": 90,
        "education_match": 65,
        "missing_skills": ["Kubernetes", "Terraform"],
        "verdict": "Strong candidate with relevant experience. Minor gaps in infrastructure skills.",
    }


@pytest.fixture
def rewrite_payload():
    return {
        "rewritten_bullets": [
            "Architected scalable REST APIs handling 10K+ daily requests, reducing latency by 35%.",
            "Automated CI/CD pipeline, cutting deployment time from 45 min to 8 min.",
        ]
    }


@pytest.fixture
def trending_payload():
    return {
        "category": "backend",
        "top_skills": [
            "Python", "FastAPI", "Docker", "Kubernetes", "PostgreSQL",
            "Redis", "GraphQL", "Rust", "Go", "gRPC",
        ],
        "rising": ["Bun", "Hono", "HTMX", "Turso", "Drizzle"],
    }

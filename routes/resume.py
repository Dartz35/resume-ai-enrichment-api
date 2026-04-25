"""
All /resume/* endpoints.

Each handler:
  1. Validates input via Pydantic (done by FastAPI before the function runs).
  2. Builds a tight system prompt and a user message.
  3. Calls services/claude.py → gets a parsed dict.
  4. Validates the dict into the response Pydantic model.
  5. Returns the model (FastAPI serialises it to JSON).

Errors from Claude (non-JSON response) are caught and re-raised as HTTP 422
so the API surface stays consistent.
"""

from __future__ import annotations

from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from models.schemas import (
    ParseResumeRequest,
    ParseResumeResponse,
    RewriteRequest,
    RewriteResponse,
    ScoreResumeRequest,
    ScoreResumeResponse,
    TrendingSkillsResponse,
)
from services.gemini import call_ai_json as call_claude_json
from services.rate_limiter import enforce_rate_limit

router = APIRouter(tags=["Resume"])

# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _claude_error(detail: str) -> HTTPException:
    """Standardised 422 when Claude returns unparseable output."""
    return HTTPException(status_code=422, detail={"error": "claude_parse_error", "message": detail})


# ---------------------------------------------------------------------------
# POST /resume/parse
# ---------------------------------------------------------------------------

_PARSE_SYSTEM = """You are a resume parser API endpoint.
Extract structured information from the provided resume text.

CRITICAL: Respond with ONLY a valid JSON object — no markdown, no code fences, no explanation, no preamble.
The JSON must have exactly these top-level keys:
  name           – string or null
  email          – string or null
  phone          – string or null
  skills         – array of strings (technical and soft skills)
  experience_years – number (estimated total years of professional experience) or null
  experience     – array of objects, each: {company, title, duration, description}
  education      – array of objects, each: {institution, degree, field, year}
  languages      – array of strings (all spoken/written languages; include "English" if implied)

Use null for any field that cannot be determined. Never omit a key."""


@router.post("/parse", response_model=ParseResumeResponse)
async def parse_resume(
    body: ParseResumeRequest,
    _api_key: Optional[str] = Depends(enforce_rate_limit),
) -> ParseResumeResponse:
    """
    Parse a resume from raw text or a publicly accessible URL.
    Returns structured fields extracted by Claude.
    """
    # Resolve the resume text — either inline or fetched from URL.
    if body.text:
        resume_text = body.text
    else:
        # Fetch the file_url with a timeout and a size cap (2 MB).
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
                resp = await http.get(body.file_url)
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Could not fetch file_url: HTTP {exc.response.status_code}",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Could not fetch file_url: {exc}",
            ) from exc

        content_type = resp.headers.get("content-type", "")
        if "pdf" in content_type:
            raise HTTPException(
                status_code=415,
                detail="PDF URLs are not yet supported. Extract the text first and use the 'text' field.",
            )

        try:
            resume_text = resp.text
        except Exception as exc:
            raise HTTPException(
                status_code=415,
                detail=f"Could not decode URL content as text: {exc}",
            ) from exc

    lang_hint = f" The resume is written in: {body.language}." if body.language else ""
    user_msg = f"Parse this resume and return the JSON.{lang_hint}\n\n{resume_text}"

    try:
        data = await call_claude_json(_PARSE_SYSTEM, user_msg, max_tokens=2048)
    except ValueError as exc:
        raise _claude_error(str(exc)) from exc

    # Coerce nested dicts into Pydantic models.
    try:
        return ParseResumeResponse(**data)
    except Exception as exc:
        raise _claude_error(f"Claude JSON did not match expected schema: {exc}") from exc


# ---------------------------------------------------------------------------
# POST /resume/score
# ---------------------------------------------------------------------------

_SCORE_SYSTEM = """You are a resume scoring API endpoint.
Compare the provided resume against the job description and score the match.

CRITICAL: Respond with ONLY a valid JSON object — no markdown, no code fences, no explanation.
The JSON must have exactly these top-level keys:
  overall_score    – integer 0-100 (weighted composite score)
  skill_match      – integer 0-100 (percentage of JD-required skills found in resume)
  experience_match – integer 0-100 (how well the experience level and type match the JD)
  education_match  – integer 0-100 (how well the education matches the JD requirements)
  missing_skills   – array of strings (required skills mentioned in JD but absent from resume)
  verdict          – string (1–2 sentence hiring recommendation, e.g. "Strong match…" or "Gaps in…")

Use the provided weights to compute overall_score = (skill_match * w_skills) + (experience_match * w_exp) + (education_match * w_edu).
Round overall_score to the nearest integer."""


@router.post("/score", response_model=ScoreResumeResponse)
async def score_resume(
    body: ScoreResumeRequest,
    _api_key: Optional[str] = Depends(enforce_rate_limit),
) -> ScoreResumeResponse:
    """
    Score a resume against a job description.
    Returns component scores (0–100), missing skills, and a hiring verdict.
    """
    weights = body.weights or body.weights.__class__() if body.weights else None
    # Fall back to default weights when not provided.
    w_skills = body.weights.skills if body.weights else 0.4
    w_exp = body.weights.experience if body.weights else 0.4
    w_edu = body.weights.education if body.weights else 0.2

    user_msg = (
        f"SCORING WEIGHTS: skills={w_skills}, experience={w_exp}, education={w_edu}\n\n"
        f"--- RESUME ---\n{body.resume_text}\n\n"
        f"--- JOB DESCRIPTION ---\n{body.job_description}"
    )

    try:
        data = await call_claude_json(_SCORE_SYSTEM, user_msg, max_tokens=2048)
    except ValueError as exc:
        raise _claude_error(str(exc)) from exc

    try:
        return ScoreResumeResponse(**data)
    except Exception as exc:
        raise _claude_error(f"Claude JSON did not match expected schema: {exc}") from exc


# ---------------------------------------------------------------------------
# POST /resume/rewrite
# ---------------------------------------------------------------------------

_REWRITE_SYSTEM = """You are a resume writer API endpoint.
Rewrite the provided bullet points to be stronger, more impactful, and ATS-friendly.

Rules:
  - Start each bullet with a strong past-tense action verb.
  - Add quantifiable metrics where clearly implied (e.g. "improved speed" → "improved speed by ~30%").
  - Apply the specified tone:
      formal  → polished, professional, third-person-readable language
      concise → short punchy bullets, max ~12 words each
      impact  → lead with achievement, include numbers, start with power verbs

CRITICAL: Respond with ONLY a valid JSON object — no markdown, no code fences, no explanation.
The JSON must have exactly one key:
  rewritten_bullets – array of strings, same count as the input bullets, in the same order."""


@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_bullets(
    body: RewriteRequest,
    _api_key: Optional[str] = Depends(enforce_rate_limit),
) -> RewriteResponse:
    """
    Rewrite resume bullet points with stronger action verbs and metrics.
    Returns the same number of bullets as submitted, in the same order.
    """
    numbered = "\n".join(f"{i+1}. {b}" for i, b in enumerate(body.bullets))
    user_msg = (
        f"Target role: {body.target_role}\n"
        f"Tone: {body.tone}\n\n"
        f"Rewrite these {len(body.bullets)} bullet points:\n{numbered}"
    )

    try:
        data = await call_claude_json(_REWRITE_SYSTEM, user_msg, max_tokens=1024)
    except ValueError as exc:
        raise _claude_error(str(exc)) from exc

    try:
        result = RewriteResponse(**data)
    except Exception as exc:
        raise _claude_error(f"Claude JSON did not match expected schema: {exc}") from exc

    # Verify Claude returned the correct bullet count.
    if len(result.rewritten_bullets) != len(body.bullets):
        raise _claude_error(
            f"Claude returned {len(result.rewritten_bullets)} bullets but {len(body.bullets)} were submitted."
        )

    return result


# ---------------------------------------------------------------------------
# GET /resume/skills/trending
# ---------------------------------------------------------------------------

_TRENDING_SYSTEM = """You are a tech job market analyst API endpoint.
Provide trending skills based on your training knowledge of job postings and industry demand.

CRITICAL: Respond with ONLY a valid JSON object — no markdown, no code fences, no explanation.
The JSON must have exactly these top-level keys:
  category   – string (the requested category, normalised/cleaned)
  top_skills – array of exactly 10 strings (most in-demand skills right now)
  rising     – array of exactly 5 strings (rapidly growing skills to watch)

Skills should be specific and actionable (e.g. "Kubernetes" not "containers")."""


@router.get("/skills/trending", response_model=TrendingSkillsResponse)
async def trending_skills(
    category: str = Query(..., description="Skill category, e.g. 'backend', 'data science', 'devops'"),
    region: str = Query(default="US", description="ISO country code, e.g. 'US', 'CA', 'GB'"),
    _api_key: Optional[str] = Depends(enforce_rate_limit),
) -> TrendingSkillsResponse:
    """
    Return the top 10 in-demand and 5 rising skills for a given category and region.
    Data is derived from Claude's training knowledge of job market trends.
    """
    user_msg = (
        f"Provide trending skills for category='{category}' in region='{region}'. "
        "Return the JSON as instructed."
    )

    try:
        data = await call_claude_json(_TRENDING_SYSTEM, user_msg, max_tokens=2048)
    except ValueError as exc:
        raise _claude_error(str(exc)) from exc

    try:
        return TrendingSkillsResponse(**data)
    except Exception as exc:
        raise _claude_error(f"Claude JSON did not match expected schema: {exc}") from exc

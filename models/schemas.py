"""
Pydantic models for all request/response schemas.
All fields are validated at the boundary so routes stay clean.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# /resume/parse
# ---------------------------------------------------------------------------

class ParseResumeRequest(BaseModel):
    text: Optional[str] = None
    file_url: Optional[str] = None
    language: Optional[str] = "en"

    @model_validator(mode="after")
    def require_text_or_url(self) -> ParseResumeRequest:
        if not self.text and not self.file_url:
            raise ValueError("Provide either 'text' or 'file_url'.")
        return self


class ExperienceEntry(BaseModel):
    company: str
    title: str
    duration: Optional[str] = None
    description: Optional[str] = None


class EducationEntry(BaseModel):
    institution: str
    degree: Optional[str] = None
    field: Optional[str] = None
    year: Optional[str] = None


class ParseResumeResponse(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = []
    experience_years: Optional[float] = None
    experience: List[ExperienceEntry] = []
    education: List[EducationEntry] = []
    languages: List[str] = []


# ---------------------------------------------------------------------------
# /resume/score
# ---------------------------------------------------------------------------

class ScoreWeights(BaseModel):
    skills: float = 0.4
    experience: float = 0.4
    education: float = 0.2

    @model_validator(mode="after")
    def weights_must_sum_to_one(self) -> ScoreWeights:
        total = self.skills + self.experience + self.education
        if abs(total - 1.0) > 0.05:
            raise ValueError(f"Weights must sum to 1.0 (got {total:.2f}).")
        return self


class ScoreResumeRequest(BaseModel):
    resume_text: str
    job_description: str
    weights: Optional[ScoreWeights] = None


class ScoreResumeResponse(BaseModel):
    overall_score: float = Field(..., ge=0, le=100)
    skill_match: float = Field(..., ge=0, le=100)
    experience_match: float = Field(..., ge=0, le=100)
    education_match: float = Field(..., ge=0, le=100)
    missing_skills: List[str]
    verdict: str


# ---------------------------------------------------------------------------
# /resume/rewrite
# ---------------------------------------------------------------------------

class RewriteRequest(BaseModel):
    bullets: List[str] = Field(..., min_length=1, max_length=25)
    target_role: str
    tone: Literal["formal", "concise", "impact"]


class RewriteResponse(BaseModel):
    rewritten_bullets: List[str]


# ---------------------------------------------------------------------------
# /resume/skills/trending
# ---------------------------------------------------------------------------

class TrendingSkillsResponse(BaseModel):
    category: str
    top_skills: List[str]
    rising: List[str]


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    version: str

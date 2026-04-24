"""Tests for POST /resume/score."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

ENDPOINT = "/resume/score"
AUTH = {"X-API-Key": "test-key"}

RESUME = "Alice Smith, 5 years Python, Django, PostgreSQL, AWS"
JD = "Senior Python engineer. Required: FastAPI, Docker, Kubernetes. Nice: AWS."


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

def test_score_returns_200(client, mocker, score_payload):
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=score_payload)

    r = client.post(ENDPOINT, json={"resume_text": RESUME, "job_description": JD}, headers=AUTH)

    assert r.status_code == 200


def test_score_response_shape(client, mocker, score_payload):
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=score_payload)

    body = client.post(ENDPOINT, json={"resume_text": RESUME, "job_description": JD}, headers=AUTH).json()

    assert 0 <= body["overall_score"] <= 100
    assert 0 <= body["skill_match"] <= 100
    assert 0 <= body["experience_match"] <= 100
    assert 0 <= body["education_match"] <= 100
    assert isinstance(body["missing_skills"], list)
    assert isinstance(body["verdict"], str)


def test_score_without_weights_uses_defaults(client, mocker, score_payload):
    """Omitting weights should use the 0.4/0.4/0.2 defaults."""
    mock_claude = mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        return_value=score_payload,
    )

    client.post(ENDPOINT, json={"resume_text": RESUME, "job_description": JD}, headers=AUTH)

    _, user_msg, *_ = mock_claude.call_args[0]
    assert "skills=0.4" in user_msg
    assert "experience=0.4" in user_msg
    assert "education=0.2" in user_msg


def test_score_custom_weights_forwarded_to_claude(client, mocker, score_payload):
    """Custom weights should appear verbatim in the user message sent to Claude."""
    mock_claude = mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        return_value=score_payload,
    )

    client.post(
        ENDPOINT,
        json={
            "resume_text": RESUME,
            "job_description": JD,
            "weights": {"skills": 0.5, "experience": 0.3, "education": 0.2},
        },
        headers=AUTH,
    )

    _, user_msg, *_ = mock_claude.call_args[0]
    assert "skills=0.5" in user_msg
    assert "experience=0.3" in user_msg
    assert "education=0.2" in user_msg


def test_score_missing_skills_empty_list(client, mocker):
    """Candidate with all skills should return an empty missing_skills list."""
    perfect = {
        "overall_score": 100,
        "skill_match": 100,
        "experience_match": 100,
        "education_match": 100,
        "missing_skills": [],
        "verdict": "Perfect match.",
    }
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=perfect)

    body = client.post(ENDPOINT, json={"resume_text": RESUME, "job_description": JD}, headers=AUTH).json()

    assert body["missing_skills"] == []
    assert body["overall_score"] == 100


# ---------------------------------------------------------------------------
# Input-validation tests
# ---------------------------------------------------------------------------

def test_score_missing_resume_text_returns_422(client):
    r = client.post(ENDPOINT, json={"job_description": JD}, headers=AUTH)
    assert r.status_code == 422


def test_score_missing_job_description_returns_422(client):
    r = client.post(ENDPOINT, json={"resume_text": RESUME}, headers=AUTH)
    assert r.status_code == 422


def test_score_weights_not_summing_to_one_returns_422(client):
    r = client.post(
        ENDPOINT,
        json={
            "resume_text": RESUME,
            "job_description": JD,
            "weights": {"skills": 0.9, "experience": 0.9, "education": 0.9},
        },
        headers=AUTH,
    )
    assert r.status_code == 422


def test_score_weights_within_tolerance_accepted(client, mocker, score_payload):
    """Weights summing to 1.0 exactly (within 0.05 tolerance) should pass validation."""
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=score_payload)

    r = client.post(
        ENDPOINT,
        json={
            "resume_text": RESUME,
            "job_description": JD,
            "weights": {"skills": 0.34, "experience": 0.33, "education": 0.33},
        },
        headers=AUTH,
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Claude error handling
# ---------------------------------------------------------------------------

def test_score_claude_invalid_json_returns_422(client, mocker):
    mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        side_effect=ValueError("Claude returned non-JSON output."),
    )

    r = client.post(ENDPOINT, json={"resume_text": RESUME, "job_description": JD}, headers=AUTH)

    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "claude_parse_error"


def test_score_out_of_range_score_rejected_by_pydantic(client, mocker):
    """Pydantic should reject scores outside [0, 100]."""
    bad = {
        "overall_score": 150,  # > 100
        "skill_match": 80,
        "experience_match": 80,
        "education_match": 80,
        "missing_skills": [],
        "verdict": "Great.",
    }
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=bad)

    r = client.post(ENDPOINT, json={"resume_text": RESUME, "job_description": JD}, headers=AUTH)

    assert r.status_code == 422

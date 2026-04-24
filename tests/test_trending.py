"""Tests for GET /resume/skills/trending."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

ENDPOINT = "/resume/skills/trending"
AUTH = {"X-API-Key": "test-key"}


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

def test_trending_returns_200(client, mocker, trending_payload):
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=trending_payload)

    r = client.get(ENDPOINT, params={"category": "backend"}, headers=AUTH)

    assert r.status_code == 200


def test_trending_response_shape(client, mocker, trending_payload):
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=trending_payload)

    body = client.get(ENDPOINT, params={"category": "backend"}, headers=AUTH).json()

    assert "category" in body
    assert "top_skills" in body
    assert "rising" in body
    assert isinstance(body["top_skills"], list)
    assert isinstance(body["rising"], list)


def test_trending_default_region_is_us(client, mocker, trending_payload):
    """When region is omitted the user message should default to US."""
    mock_claude = mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        return_value=trending_payload,
    )

    client.get(ENDPOINT, params={"category": "devops"}, headers=AUTH)

    _, user_msg, *_ = mock_claude.call_args[0]
    assert "US" in user_msg


def test_trending_custom_region_forwarded(client, mocker, trending_payload):
    mock_claude = mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        return_value=trending_payload,
    )

    client.get(ENDPOINT, params={"category": "data science", "region": "GB"}, headers=AUTH)

    _, user_msg, *_ = mock_claude.call_args[0]
    assert "GB" in user_msg


def test_trending_category_forwarded_to_claude(client, mocker, trending_payload):
    mock_claude = mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        return_value=trending_payload,
    )

    client.get(ENDPOINT, params={"category": "mobile"}, headers=AUTH)

    _, user_msg, *_ = mock_claude.call_args[0]
    assert "mobile" in user_msg


@pytest.mark.parametrize("category", ["backend", "frontend", "data science", "devops", "mobile", "security"])
def test_trending_various_categories_accepted(client, mocker, trending_payload, category):
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=trending_payload)

    r = client.get(ENDPOINT, params={"category": category}, headers=AUTH)

    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Input-validation tests
# ---------------------------------------------------------------------------

def test_trending_missing_category_returns_422(client):
    """category is a required query param."""
    r = client.get(ENDPOINT, headers=AUTH)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Claude error handling
# ---------------------------------------------------------------------------

def test_trending_claude_invalid_json_returns_422(client, mocker):
    mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        side_effect=ValueError("Claude returned non-JSON output."),
    )

    r = client.get(ENDPOINT, params={"category": "backend"}, headers=AUTH)

    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "claude_parse_error"


def test_trending_no_auth_still_works_free_tier(client, mocker, trending_payload):
    """The endpoint should work without an API key (free tier)."""
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=trending_payload)

    r = client.get(ENDPOINT, params={"category": "backend"})

    assert r.status_code == 200

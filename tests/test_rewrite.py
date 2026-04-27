"""Tests for POST /resume/rewrite."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

ENDPOINT = "/resume/rewrite"
AUTH = {"X-API-Key": "test-key"}

BULLETS = [
    "worked on improving the checkout flow",
    "helped with customer support tickets",
]

BASE_BODY = {
    "bullets": BULLETS,
    "target_role": "Senior Product Engineer",
    "tone": "impact",
}


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

def test_rewrite_returns_200(client, mocker, rewrite_payload):
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=rewrite_payload)

    r = client.post(ENDPOINT, json=BASE_BODY, headers=AUTH)

    assert r.status_code == 200


def test_rewrite_response_shape(client, mocker, rewrite_payload):
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=rewrite_payload)

    body = client.post(ENDPOINT, json=BASE_BODY, headers=AUTH).json()

    assert "rewritten_bullets" in body
    assert isinstance(body["rewritten_bullets"], list)
    assert len(body["rewritten_bullets"]) == len(BULLETS)


@pytest.mark.parametrize("tone", ["formal", "concise", "impact"])
def test_rewrite_all_tones_accepted(client, mocker, rewrite_payload, tone):
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=rewrite_payload)

    r = client.post(ENDPOINT, json={**BASE_BODY, "tone": tone}, headers=AUTH)

    assert r.status_code == 200


def test_rewrite_tone_forwarded_to_claude(client, mocker, rewrite_payload):
    mock_claude = mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        return_value=rewrite_payload,
    )

    client.post(ENDPOINT, json={**BASE_BODY, "tone": "concise"}, headers=AUTH)

    _, user_msg, *_ = mock_claude.call_args[0]
    assert "concise" in user_msg


def test_rewrite_target_role_forwarded_to_claude(client, mocker, rewrite_payload):
    mock_claude = mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        return_value=rewrite_payload,
    )

    client.post(ENDPOINT, json=BASE_BODY, headers=AUTH)

    _, user_msg, *_ = mock_claude.call_args[0]
    assert "Senior Product Engineer" in user_msg


def test_rewrite_bullets_numbered_in_user_message(client, mocker, rewrite_payload):
    """Bullets should be numbered in the user message for clarity."""
    mock_claude = mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        return_value=rewrite_payload,
    )

    client.post(ENDPOINT, json=BASE_BODY, headers=AUTH)

    _, user_msg, *_ = mock_claude.call_args[0]
    assert "1." in user_msg
    assert "2." in user_msg


def test_rewrite_single_bullet(client, mocker):
    single_rewrite = {"rewritten_bullets": ["Reduced cart abandonment by 18% through checkout redesign."]}
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=single_rewrite)

    r = client.post(
        ENDPOINT,
        json={"bullets": ["improved checkout"], "target_role": "PM", "tone": "impact"},
        headers=AUTH,
    )

    assert r.status_code == 200
    assert len(r.json()["rewritten_bullets"]) == 1


# ---------------------------------------------------------------------------
# Input-validation tests
# ---------------------------------------------------------------------------

def test_rewrite_invalid_tone_returns_422(client):
    r = client.post(ENDPOINT, json={**BASE_BODY, "tone": "aggressive"}, headers=AUTH)
    assert r.status_code == 422


def test_rewrite_empty_bullets_returns_422(client):
    r = client.post(ENDPOINT, json={**BASE_BODY, "bullets": []}, headers=AUTH)
    assert r.status_code == 422


def test_rewrite_missing_target_role_returns_422(client):
    body = {k: v for k, v in BASE_BODY.items() if k != "target_role"}
    r = client.post(ENDPOINT, json=body, headers=AUTH)
    assert r.status_code == 422


def test_rewrite_missing_tone_returns_422(client):
    body = {k: v for k, v in BASE_BODY.items() if k != "tone"}
    r = client.post(ENDPOINT, json=body, headers=AUTH)
    assert r.status_code == 422


def test_rewrite_too_many_bullets_returns_422(client):
    r = client.post(
        ENDPOINT,
        json={**BASE_BODY, "bullets": ["bullet"] * 26},  # max is 25
        headers=AUTH,
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Claude error handling
# ---------------------------------------------------------------------------

def test_rewrite_claude_invalid_json_returns_422(client, mocker):
    mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        side_effect=ValueError("Claude returned non-JSON output."),
    )

    r = client.post(ENDPOINT, json=BASE_BODY, headers=AUTH)

    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "claude_parse_error"


def test_rewrite_wrong_bullet_count_from_claude_returns_422(client, mocker):
    """If Claude returns a different number of bullets than submitted, return 422."""
    # We submit 2 bullets but Claude returns only 1.
    mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        return_value={"rewritten_bullets": ["Only one bullet back."]},
    )

    r = client.post(ENDPOINT, json=BASE_BODY, headers=AUTH)

    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "claude_parse_error"

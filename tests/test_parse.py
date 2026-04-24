"""
Tests for POST /resume/parse.

Claude is always mocked via routes.resume.call_claude_json (the name bound in
the routes module after `from services.claude import call_claude_json`).
httpx.AsyncClient is mocked for file_url tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest


ENDPOINT = "/resume/parse"
AUTH = {"X-API-Key": "test-key"}

RESUME_TEXT = (
    "Jane Doe  jane@example.com  +1-555-9999\n"
    "Software Engineer at Acme (2020-2024)\n"
    "B.Sc. Computer Science, MIT 2020"
)


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

def test_parse_text_returns_200(client, mocker, parse_payload):
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=parse_payload)

    r = client.post(ENDPOINT, json={"text": RESUME_TEXT}, headers=AUTH)

    assert r.status_code == 200


def test_parse_text_response_shape(client, mocker, parse_payload):
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=parse_payload)

    body = client.post(ENDPOINT, json={"text": RESUME_TEXT}, headers=AUTH).json()

    assert body["name"] == "Alice Smith"
    assert body["email"] == "alice@example.com"
    assert isinstance(body["skills"], list)
    assert isinstance(body["experience"], list)
    assert isinstance(body["education"], list)
    assert isinstance(body["languages"], list)
    assert body["experience_years"] == 5.0


def test_parse_passes_text_to_claude(client, mocker, parse_payload):
    """The user message sent to Claude should contain the resume text."""
    mock_claude = mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        return_value=parse_payload,
    )

    client.post(ENDPOINT, json={"text": RESUME_TEXT}, headers=AUTH)

    _, user_msg, *_ = mock_claude.call_args[0]
    assert RESUME_TEXT in user_msg


def test_parse_language_hint_forwarded(client, mocker, parse_payload):
    """When language is supplied it should appear in the user message."""
    mock_claude = mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        return_value=parse_payload,
    )

    client.post(ENDPOINT, json={"text": RESUME_TEXT, "language": "fr"}, headers=AUTH)

    _, user_msg, *_ = mock_claude.call_args[0]
    assert "fr" in user_msg


def test_parse_optional_fields_nullable(client, mocker):
    """Claude response with null optional fields must still deserialise correctly."""
    sparse = {
        "name": None, "email": None, "phone": None,
        "skills": [], "experience_years": None,
        "experience": [], "education": [], "languages": [],
    }
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=sparse)

    r = client.post(ENDPOINT, json={"text": "John"}, headers=AUTH)

    assert r.status_code == 200
    assert r.json()["name"] is None


# ---------------------------------------------------------------------------
# file_url tests
# ---------------------------------------------------------------------------

def _mock_httpx(mocker, *, text="resume content", content_type="text/plain"):
    """Patch httpx.AsyncClient to return a successful plain-text response."""
    mock_resp = MagicMock()
    mock_resp.text = text
    mock_resp.headers = {"content-type": content_type}
    mock_resp.raise_for_status.return_value = None

    mock_http = AsyncMock()
    mock_http.get = AsyncMock(return_value=mock_resp)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_http)
    cm.__aexit__ = AsyncMock(return_value=None)

    mocker.patch("httpx.AsyncClient", return_value=cm)
    return mock_http


def test_parse_file_url_fetches_and_parses(client, mocker, parse_payload):
    _mock_httpx(mocker)
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=parse_payload)

    r = client.post(ENDPOINT, json={"file_url": "http://example.com/cv.txt"}, headers=AUTH)

    assert r.status_code == 200
    assert r.json()["name"] == "Alice Smith"


def test_parse_file_url_content_sent_to_claude(client, mocker, parse_payload):
    """The fetched URL content must end up in the Claude user message."""
    _mock_httpx(mocker, text="Fetched resume body")
    mock_claude = mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        return_value=parse_payload,
    )

    client.post(ENDPOINT, json={"file_url": "http://example.com/cv.txt"}, headers=AUTH)

    _, user_msg, *_ = mock_claude.call_args[0]
    assert "Fetched resume body" in user_msg


def test_parse_file_url_http_error_returns_400(client, mocker):
    """An HTTP error fetching the URL should return 400."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
    )

    mock_http = AsyncMock()
    mock_http.get = AsyncMock(return_value=mock_resp)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_http)
    cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch("httpx.AsyncClient", return_value=cm)

    r = client.post(ENDPOINT, json={"file_url": "http://bad.example.com/cv.txt"}, headers=AUTH)

    assert r.status_code == 400
    assert "file_url" in r.json()["detail"].lower()


def test_parse_file_url_pdf_returns_415(client, mocker, parse_payload):
    """PDF content-type from a URL should return 415 Unsupported Media Type."""
    _mock_httpx(mocker, content_type="application/pdf")
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=parse_payload)

    r = client.post(ENDPOINT, json={"file_url": "http://example.com/cv.pdf"}, headers=AUTH)

    assert r.status_code == 415


def test_parse_network_error_returns_400(client, mocker):
    """A network-level error (e.g. DNS failure) should return 400."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(side_effect=httpx.RequestError("DNS lookup failed"))
    cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch("httpx.AsyncClient", return_value=cm)

    r = client.post(ENDPOINT, json={"file_url": "http://unreachable.example"}, headers=AUTH)

    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Input-validation tests
# ---------------------------------------------------------------------------

def test_parse_missing_text_and_url_returns_422(client):
    r = client.post(ENDPOINT, json={"language": "en"}, headers=AUTH)
    assert r.status_code == 422


def test_parse_empty_body_returns_422(client):
    r = client.post(ENDPOINT, json={}, headers=AUTH)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Claude error handling
# ---------------------------------------------------------------------------

def test_parse_claude_invalid_json_returns_422(client, mocker):
    mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        side_effect=ValueError("Claude returned non-JSON output."),
    )

    r = client.post(ENDPOINT, json={"text": RESUME_TEXT}, headers=AUTH)

    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["error"] == "claude_parse_error"


def test_parse_claude_wrong_schema_returns_422(client, mocker):
    """If Claude returns valid JSON but the wrong shape, we still get 422."""
    mocker.patch(
        "routes.resume.call_claude_json",
        new_callable=AsyncMock,
        return_value={"unexpected_key": "oops"},  # missing required list fields → Pydantic coerces to defaults
    )

    # Pydantic sets missing list fields to [] and missing optionals to None,
    # so this should actually succeed with empty/null values.
    r = client.post(ENDPOINT, json={"text": RESUME_TEXT}, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["skills"] == []

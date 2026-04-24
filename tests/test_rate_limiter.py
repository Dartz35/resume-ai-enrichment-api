"""
Tests for the rate-limiting layer.

Two kinds of tests:
  1. Unit tests on InMemoryRateLimiter directly (no HTTP).
  2. Integration tests via the TestClient that verify HTTP 429 behaviour
     and that free / paid tiers use independent counters.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

PARSE_ENDPOINT = "/resume/parse"
PARSE_BODY = {"text": "Alice Smith, engineer."}


# ---------------------------------------------------------------------------
# Unit tests — InMemoryRateLimiter
# ---------------------------------------------------------------------------

class TestInMemoryRateLimiter:
    def test_allows_up_to_limit(self):
        from services.rate_limiter import InMemoryRateLimiter

        rl = InMemoryRateLimiter()
        for i in range(10):
            allowed, count = rl.check("key", 10)
            assert allowed, f"Request {i+1} should be allowed"
            assert count == i + 1

    def test_blocks_at_limit_plus_one(self):
        from services.rate_limiter import InMemoryRateLimiter

        rl = InMemoryRateLimiter()
        for _ in range(5):
            rl.check("key", 5)

        allowed, count = rl.check("key", 5)
        assert not allowed
        assert count == 6

    def test_different_keys_are_independent(self):
        from services.rate_limiter import InMemoryRateLimiter

        rl = InMemoryRateLimiter()
        for _ in range(50):
            rl.check("ip:1.2.3.4", 50)

        # A different key should still have a fresh counter.
        allowed, count = rl.check("ip:9.9.9.9", 50)
        assert allowed
        assert count == 1

    def test_counter_increments_monotonically(self):
        from services.rate_limiter import InMemoryRateLimiter

        rl = InMemoryRateLimiter()
        previous = 0
        for _ in range(20):
            _, count = rl.check("k", 1000)
            assert count > previous
            previous = count

    def test_free_tier_limit_constant(self):
        from services.rate_limiter import FREE_TIER_LIMIT
        assert FREE_TIER_LIMIT == 7

    def test_paid_tier_limit_constant(self):
        from services.rate_limiter import PAID_TIER_LIMIT
        assert PAID_TIER_LIMIT == 2000

    def test_pro_tier_limit_constant(self):
        from services.rate_limiter import PRO_TIER_LIMIT
        assert PRO_TIER_LIMIT == 500

    def test_ultra_tier_limit_constant(self):
        from services.rate_limiter import ULTRA_TIER_LIMIT
        assert ULTRA_TIER_LIMIT == 2000

    def test_mega_tier_limit_constant(self):
        from services.rate_limiter import MEGA_TIER_LIMIT
        assert MEGA_TIER_LIMIT == 10000


# ---------------------------------------------------------------------------
# Integration tests — HTTP 429 via TestClient
# ---------------------------------------------------------------------------

def test_free_tier_hit_7_requests_all_pass(client, mocker, parse_payload):
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=parse_payload)

    for i in range(7):
        r = client.post(PARSE_ENDPOINT, json=PARSE_BODY)
        assert r.status_code == 200, f"Request {i+1} should pass"


def test_free_tier_8th_request_is_rejected(client, mocker, parse_payload):
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=parse_payload)

    for _ in range(7):
        client.post(PARSE_ENDPOINT, json=PARSE_BODY)

    r = client.post(PARSE_ENDPOINT, json=PARSE_BODY)
    assert r.status_code == 429


def test_rate_limit_error_body(client, mocker, parse_payload):
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=parse_payload)

    for _ in range(7):
        client.post(PARSE_ENDPOINT, json=PARSE_BODY)

    r = client.post(PARSE_ENDPOINT, json=PARSE_BODY)
    detail = r.json()["detail"]
    assert detail["error"] == "rate_limit_exceeded"
    assert detail["tier"] == "basic"
    assert detail["limit"] == 7


def test_paid_tier_key_has_higher_limit(client, mocker, parse_payload):
    """Direct paid callers (X-API-Key only) get the ULTRA limit (2000/day)."""
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=parse_payload)
    headers = {"X-API-Key": "my-paid-key"}

    # Make 51 requests — all should pass because the paid limit is 2000.
    for i in range(51):
        r = client.post(PARSE_ENDPOINT, json=PARSE_BODY, headers=headers)
        assert r.status_code == 200, f"Paid request {i+1} should not be rate-limited"


def test_free_and_paid_tiers_have_independent_counters(client, mocker, parse_payload):
    """Exhausting the free-tier quota must not affect the paid-tier counter."""
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=parse_payload)

    # Exhaust free tier.
    for _ in range(7):
        client.post(PARSE_ENDPOINT, json=PARSE_BODY)

    assert client.post(PARSE_ENDPOINT, json=PARSE_BODY).status_code == 429

    # Paid tier should be unaffected.
    r = client.post(PARSE_ENDPOINT, json=PARSE_BODY, headers={"X-API-Key": "premium"})
    assert r.status_code == 200


def test_different_api_keys_have_independent_counters(client, mocker, parse_payload):
    """Two distinct API keys must not share their quota."""
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=parse_payload)

    key_a = {"X-API-Key": "key-alpha"}
    key_b = {"X-API-Key": "key-beta"}

    # Exhaust key_a up to just below the *free* limit using 50 requests — but
    # these are paid-tier so actually limited at 2000.  Just verify isolation.
    for _ in range(50):
        client.post(PARSE_ENDPOINT, json=PARSE_BODY, headers=key_a)

    r = client.post(PARSE_ENDPOINT, json=PARSE_BODY, headers=key_b)
    assert r.status_code == 200


def test_429_response_includes_tier_info(client, mocker, parse_payload):
    """429 response body should tell the caller their tier and the limit."""
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=parse_payload)

    for _ in range(7):
        client.post(PARSE_ENDPOINT, json=PARSE_BODY)

    r = client.post(PARSE_ENDPOINT, json=PARSE_BODY)
    detail = r.json()["detail"]
    assert "limit" in detail
    assert "tier" in detail
    assert "count" in detail


# ---------------------------------------------------------------------------
# RapidAPI subscription tier tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("subscription,expected_limit,expected_tier", [
    ("PRO",   500,   "pro"),
    ("ULTRA", 2000,  "ultra"),
    ("MEGA",  10000, "mega"),
    ("BASIC", 7,     "basic"),
])
def test_rapidapi_subscription_header_sets_correct_limit(
    client, mocker, parse_payload, subscription, expected_limit, expected_tier
):
    """X-RapidAPI-Subscription header should select the correct tier and limit."""
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=parse_payload)
    headers = {"X-API-Key": "some-key", "X-RapidAPI-Subscription": subscription}

    # Exhaust quota then check the 429 reports the right tier and limit.
    for _ in range(expected_limit):
        client.post(PARSE_ENDPOINT, json=PARSE_BODY, headers=headers)

    r = client.post(PARSE_ENDPOINT, json=PARSE_BODY, headers=headers)
    assert r.status_code == 429
    detail = r.json()["detail"]
    assert detail["tier"] == expected_tier
    assert detail["limit"] == expected_limit


def test_pro_tier_allows_500_requests(client, mocker, parse_payload):
    """PRO tier should allow exactly 500 requests before blocking."""
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=parse_payload)
    headers = {"X-API-Key": "pro-key", "X-RapidAPI-Subscription": "PRO"}

    for i in range(500):
        r = client.post(PARSE_ENDPOINT, json=PARSE_BODY, headers=headers)
        assert r.status_code == 200, f"PRO request {i+1} should be allowed"

    r = client.post(PARSE_ENDPOINT, json=PARSE_BODY, headers=headers)
    assert r.status_code == 429


def test_different_subscription_tiers_have_independent_counters(client, mocker, parse_payload):
    """Exhausting PRO quota must not affect a MEGA caller."""
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=parse_payload)

    pro_headers  = {"X-API-Key": "pro-key",  "X-RapidAPI-Subscription": "PRO"}
    mega_headers = {"X-API-Key": "mega-key", "X-RapidAPI-Subscription": "MEGA"}

    for _ in range(500):
        client.post(PARSE_ENDPOINT, json=PARSE_BODY, headers=pro_headers)

    assert client.post(PARSE_ENDPOINT, json=PARSE_BODY, headers=pro_headers).status_code == 429
    assert client.post(PARSE_ENDPOINT, json=PARSE_BODY, headers=mega_headers).status_code == 200


def test_no_subscription_header_with_api_key_uses_ultra_limit(client, mocker, parse_payload):
    """Direct callers with X-API-Key but no subscription header get ULTRA (2000/day)."""
    mocker.patch("routes.resume.call_claude_json", new_callable=AsyncMock, return_value=parse_payload)
    headers = {"X-API-Key": "direct-caller"}

    # 51 requests should all pass (well above free, within ultra).
    for i in range(51):
        r = client.post(PARSE_ENDPOINT, json=PARSE_BODY, headers=headers)
        assert r.status_code == 200, f"Request {i+1} should be allowed on ultra limit"

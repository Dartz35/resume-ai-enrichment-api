"""Tests for GET /health."""


def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_health_body(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"


def test_health_no_auth_required(client):
    """Health endpoint must be accessible without any API key."""
    r = client.get("/health")
    assert r.status_code == 200


def test_health_not_rate_limited(client):
    """Health endpoint should not consume rate limit quota."""
    from services.rate_limiter import rate_limiter, FREE_TIER_LIMIT

    for _ in range(FREE_TIER_LIMIT + 5):
        r = client.get("/health")
        assert r.status_code == 200

    # Rate limiter store should still be empty — /health has no Depends(enforce_rate_limit)
    assert len(rate_limiter._store) == 0

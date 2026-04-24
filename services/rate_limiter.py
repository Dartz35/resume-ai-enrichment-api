"""
In-memory daily rate limiter with four RapidAPI pricing tiers.

Tier detection uses the X-RapidAPI-Subscription header that RapidAPI injects
on every proxied request.  Direct callers (no header) fall back to the free
tier keyed by IP address.

Tier limits (requests / day):
  BASIC  (free)  →  50
  PRO            →  500
  ULTRA          →  2 000
  MEGA           →  10 000

For production at scale, replace _store with Redis (e.g. via redis-py async).
This implementation uses a threading.Lock so it is safe under uvicorn's default
single-process / multi-threaded worker mode.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from threading import Lock
from typing import Optional, Tuple

from fastapi import Header, HTTPException, Request


class InMemoryRateLimiter:
    def __init__(self) -> None:
        # {identifier: {date_str: request_count}}
        self._store: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._lock = Lock()

    def check(self, key: str, limit: int) -> Tuple[bool, int]:
        """Increment counter for *key* today and return (allowed, current_count)."""
        today = date.today().isoformat()
        with self._lock:
            self._store[key][today] += 1
            count = self._store[key][today]
        return count <= limit, count


# Module-level singleton shared across all requests in the same process.
rate_limiter = InMemoryRateLimiter()


# ---------------------------------------------------------------------------
# Tier configuration
# ---------------------------------------------------------------------------

FREE_TIER_LIMIT  =      7   # BASIC  — no subscription (~200/month)
PRO_TIER_LIMIT   =    500   # PRO    — $9.99/month
ULTRA_TIER_LIMIT =  2_000   # ULTRA  — $29.99/month
MEGA_TIER_LIMIT  = 10_000   # MEGA   — $99.99/month

# PAID_TIER_LIMIT kept for backwards-compat with existing tests.
PAID_TIER_LIMIT = ULTRA_TIER_LIMIT

_SUBSCRIPTION_LIMITS: dict[str, tuple[int, str]] = {
    "BASIC": (FREE_TIER_LIMIT,  "basic"),
    "PRO":   (PRO_TIER_LIMIT,   "pro"),
    "ULTRA": (ULTRA_TIER_LIMIT, "ultra"),
    "MEGA":  (MEGA_TIER_LIMIT,  "mega"),
}


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def enforce_rate_limit(
    request: Request,
    x_api_key: Optional[str] = Header(default=None),
    x_rapidapi_subscription: Optional[str] = Header(default=None),
) -> Optional[str]:
    """
    Dependency injected into every rate-limited route.

    Priority:
      1. X-RapidAPI-Subscription header (set by RapidAPI gateway) → named tier
      2. X-API-Key present but no subscription header → ULTRA limit (direct paid caller)
      3. Neither header → free tier keyed by IP (BASIC limit)
    """
    sub = (x_rapidapi_subscription or "").upper()

    if sub in _SUBSCRIPTION_LIMITS:
        limit, tier = _SUBSCRIPTION_LIMITS[sub]
        key = f"key:{x_api_key or sub}"
    elif x_api_key:
        limit, tier = ULTRA_TIER_LIMIT, "ultra"
        key = f"key:{x_api_key}"
    else:
        limit, tier = FREE_TIER_LIMIT, "basic"
        client_ip = request.client.host if request.client else "unknown"
        key = f"ip:{client_ip}"

    allowed, count = rate_limiter.check(key, limit)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "tier": tier,
                "limit": limit,
                "count": count,
                "message": f"Daily limit of {limit} requests exceeded for {tier} tier.",
            },
        )

    return x_api_key

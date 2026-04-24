"""
Thin async wrapper around the Anthropic SDK.

All API calls funnel through call_claude_json(), which:
  1. Sends a structured system prompt + user message to Claude.
  2. Strips any accidental markdown code fences from the response.
  3. Parses and returns the raw dict.
  4. Raises ValueError (caught by callers → HTTP 422) on JSON parse failure.

Prompt caching is enabled on every system prompt via cache_control so that
repeated calls to the same endpoint benefit from the cache read discount.
"""

from __future__ import annotations

import json
import os
import re

import anthropic

# Claude Sonnet 4 (May 2025 snapshot) as specified by the project requirements.
MODEL = "claude-sonnet-4-20250514"

# Async client — works cleanly inside FastAPI's async request handlers.
_client = anthropic.AsyncAnthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
)

# Regex to strip ```json ... ``` or ``` ... ``` wrappers in case Claude
# ignores the "no markdown" instruction.
_FENCE_RE = re.compile(r"^```(?:json)?\s*([\s\S]*?)\s*```$", re.MULTILINE)


async def call_claude_json(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 2048,
) -> dict:
    """
    Call Claude with *system_prompt* and *user_message*, expecting a JSON reply.

    cache_control on the system block lets the Anthropic API cache the
    (stable) system prompt across repeated endpoint calls, reducing latency
    and cost on warm requests.

    Returns: parsed dict from Claude's response.
    Raises:  ValueError if the response is not valid JSON.
             anthropic.APIError subclasses bubble up to the route handler.
    """
    response = await _client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                # Cache the system prompt — saves tokens on repeated calls.
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown fences if Claude wrapped the JSON anyway.
    fence_match = _FENCE_RE.match(raw)
    if fence_match:
        raw = fence_match.group(1).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        preview = raw[:300]
        raise ValueError(
            f"Claude returned non-JSON output. Parse error: {exc}. "
            f"Response preview: {preview!r}"
        ) from exc

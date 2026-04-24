"""
Thin async wrapper around the Google Gemini SDK (google-genai).

All API calls funnel through call_ai_json(), which:
  1. Sends a system prompt + user message to Gemini.
  2. Strips any accidental markdown code fences from the response.
  3. Parses and returns the raw dict.
  4. Raises ValueError (caught by callers → HTTP 422) on JSON parse failure.
"""

from __future__ import annotations

import json
import os
import re

from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash"

_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))

_FENCE_RE = re.compile(r"^```(?:json)?\s*([\s\S]*?)\s*```$", re.MULTILINE)


async def call_ai_json(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 2048,
) -> dict:
    """
    Call Gemini with *system_prompt* and *user_message*, expecting a JSON reply.

    Returns: parsed dict from Gemini's response.
    Raises:  ValueError if the response is not valid JSON.
    """
    response = await _client.aio.models.generate_content(
        model=MODEL,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
        ),
    )

    raw = response.text.strip()

    fence_match = _FENCE_RE.match(raw)
    if fence_match:
        raw = fence_match.group(1).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        preview = raw[:300]
        raise ValueError(
            f"Gemini returned non-JSON output. Parse error: {exc}. "
            f"Response preview: {preview!r}"
        ) from exc

"""
engines/openai_vision.py — OpenAI GPT-4o Vision wrapper for OCR-Zen.
Model: gpt-4o (requires paid tier — free tier returns insufficient_quota).
Phase 3 implementation.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Union

import config


# ── Retry helper ─────────────────────────────────────────────────────────────

def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("429", "quota", "rate_limit", "insufficient_quota"))


def _with_retry(fn, engine_name: str, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as exc:
            # Don't retry insufficient_quota — it won't resolve with time
            if "insufficient_quota" in str(exc).lower():
                raise
            if _is_quota_error(exc) and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"[Retry {attempt + 1}/{max_retries}] {engine_name}: rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    return f"[{engine_name}: quota exhausted after {max_retries} retries]"


# ── Engine ────────────────────────────────────────────────────────────────────

class OpenAIVisionEngine:
    """
    Calls OpenAI GPT-4o Vision API to read image content.
    Note: Requires paid tier. Free tier returns [openai: insufficient quota].
    """

    name  = "openai"
    role  = "llm"
    MODEL = "gpt-4o"

    def __init__(self, api_key: str = "", rate_limiter=None):
        self.api_key      = api_key or config.OPENAI_API_KEY
        self.rate_limiter = rate_limiter
        self._client      = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def available(self) -> bool:
        return bool(self.api_key)

    def read(
        self,
        image_path: Union[str, Path],
        question: str = "Transcribe ALL text you can see in this image exactly as written. Include every word, symbol and character.",
    ) -> str:
        """
        Call GPT-4o Vision API.
        Returns '[openai: insufficient quota]' if free tier exhausted.
        Returns '[openai: {error}]' on other failures.
        """
        if not self.available():
            return "[openai: no API key configured]"

        if self.rate_limiter:
            self.rate_limiter.acquire("openai")

        def _call() -> str:
            with open(str(image_path), "rb") as f:
                img_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

            suffix = Path(image_path).suffix.lower()
            media_map = {".png": "image/png", ".jpg": "image/jpeg",
                         ".jpeg": "image/jpeg", ".gif": "image/gif",
                         ".webp": "image/webp"}
            media_type = media_map.get(suffix, "image/png")

            client   = self._get_client()
            response = client.chat.completions.create(
                model      = self.MODEL,
                max_tokens = 512,
                messages   = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type":      "image_url",
                                "image_url": {
                                    "url":    f"data:{media_type};base64,{img_b64}",
                                    "detail": "high",
                                },
                            },
                            {"type": "text", "text": question},
                        ],
                    }
                ],
            )
            return response.choices[0].message.content.strip()

        try:
            return _with_retry(_call, self.name)
        except Exception as exc:
            err = str(exc)
            if "insufficient_quota" in err.lower():
                return "[openai: insufficient quota — paid tier required]"
            if "quota" in err.lower() or "429" in err:
                return f"[openai: rate limit — {err[:120]}]"
            return f"[openai: {err[:120]}]"

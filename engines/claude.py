"""
engines/claude.py — Anthropic Claude Vision wrapper for OCR-Zen.
Model: claude-3-5-haiku-20241022 (free tier, vision capable).
claude-3-opus requires paid tier — do NOT use.
Phase 3 implementation.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Union

import config


# ── Retry helper (shared pattern with other engines) ──────────────────────────

def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("429", "quota", "rate_limit", "overloaded", "529"))


def _with_retry(fn, engine_name: str, max_retries: int = 3) -> str:
    """Exponential backoff: 2s → 4s → 8s on quota/rate errors."""
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as exc:
            if _is_quota_error(exc) and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"[Retry {attempt + 1}/{max_retries}] {engine_name}: rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    return f"[{engine_name}: quota exhausted after {max_retries} retries]"


# ── Engine ────────────────────────────────────────────────────────────────────

class ClaudeEngine:
    """
    Calls Anthropic Claude Vision API to read image content.
    Uses claude-3-5-haiku-20241022 (free tier, vision capable).
    """

    name  = "claude"
    role  = "llm"
    MODEL = "claude-3-5-haiku-20241022"

    def __init__(self, api_key: str = "", rate_limiter=None):
        self.api_key      = api_key or config.ANTHROPIC_API_KEY
        self.rate_limiter = rate_limiter
        self._client      = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def available(self) -> bool:
        return bool(self.api_key)

    def read(
        self,
        image_path: Union[str, Path],
        question: str = "Transcribe ALL text you can see in this image exactly as written. Include every word, symbol and character.",
    ) -> str:
        """
        Call Claude Vision API.
        Returns '[claude: {error}]' on failure.
        """
        if not self.available():
            return "[claude: no API key configured]"

        if self.rate_limiter:
            self.rate_limiter.acquire("claude")

        def _call() -> str:
            with open(str(image_path), "rb") as f:
                img_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

            # Detect media type from extension
            suffix = Path(image_path).suffix.lower()
            media_map = {".png": "image/png", ".jpg": "image/jpeg",
                         ".jpeg": "image/jpeg", ".gif": "image/gif",
                         ".webp": "image/webp"}
            media_type = media_map.get(suffix, "image/png")

            client  = self._get_client()
            message = client.messages.create(
                model      = self.MODEL,
                max_tokens = 1024,
                messages   = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type":       "base64",
                                    "media_type": media_type,
                                    "data":       img_b64,
                                },
                            },
                            {"type": "text", "text": question},
                        ],
                    }
                ],
            )
            return message.content[0].text.strip()

        try:
            return _with_retry(_call, self.name)
        except Exception as exc:
            err = str(exc)
            if "quota" in err.lower() or "429" in err or "529" in err:
                return f"[claude: rate limit — {err[:120]}]"
            return f"[claude: {err[:120]}]"

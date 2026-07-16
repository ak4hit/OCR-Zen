"""
engines/gemini.py — Google Gemini Vision wrapper for OCR-Zen.
Model: gemini-2.0-flash (gemini-pro-vision is deprecated — do NOT use).
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
    return any(k in msg for k in ("429", "quota", "resource_exhausted", "rate_limit"))


def _with_retry(fn, engine_name: str, max_retries: int = 3) -> str:
    """Exponential backoff: 2s → 4s → 8s on quota/rate errors."""
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as exc:
            if _is_quota_error(exc) and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"[Retry {attempt + 1}/{max_retries}] {engine_name}: 429 received, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    return f"[{engine_name}: quota exhausted after {max_retries} retries]"


# ── Engine ────────────────────────────────────────────────────────────────────

class GeminiEngine:
    """
    Calls Google Gemini Vision API to read image content.
    Uses gemini-2.0-flash — gemini-pro-vision is deprecated.
    """

    name  = "gemini"
    role  = "llm"
    MODEL = "gemini-2.0-flash"

    def __init__(self, api_key: str = "", quota_tracker=None, rate_limiter=None):
        self.api_key       = api_key or config.GOOGLE_API_KEY
        self.quota_tracker = quota_tracker
        self.rate_limiter  = rate_limiter
        self._client       = None

    def _get_client(self):
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.MODEL)
        return self._client

    def available(self) -> bool:
        return bool(self.api_key)

    def read(
        self,
        image_path: Union[str, Path],
        question: str = "Transcribe ALL text you can see in this image exactly as written. Include every word, symbol and character.",
    ) -> str:
        """
        Call Gemini Vision API.
        Returns '[gemini: {error}]' on failure.
        """
        if not self.available():
            return "[gemini: no API key configured]"

        # Rate limiter hook (Phase 6 will populate this)
        if self.rate_limiter:
            self.rate_limiter.acquire("gemini")

        # Quota tracker hook
        if self.quota_tracker:
            used, limit = self.quota_tracker.check("gemini")
            if used >= limit:
                return f"[gemini: daily quota exhausted ({used}/{limit} RPD)]"

        def _call() -> str:
            from PIL import Image as PILImage
            model = self._get_client()
            img   = PILImage.open(str(image_path))
            response = model.generate_content([question, img])
            return response.text.strip()

        try:
            result = _with_retry(_call, self.name)
            if self.quota_tracker:
                self.quota_tracker.record("gemini")
            return result
        except Exception as exc:
            err = str(exc)
            if "quota" in err.lower() or "429" in err:
                return f"[gemini: quota error — {err[:120]}]"
            return f"[gemini: {err[:120]}]"

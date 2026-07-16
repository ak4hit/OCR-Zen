"""
engines/gemini.py — Google Gemini Vision wrapper for OCR-Zen.
Model: gemini-2.0-flash (confirmed working, not deprecated).
Phase 3 will implement full API call + 429 handling + quota tracking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union


class GeminiEngine:
    """
    Calls Google Gemini Vision API to read image content.
    Uses gemini-2.0-flash (gemini-pro-vision is deprecated — do not use).
    Phase 3 implementation.
    """

    name = "gemini"
    role = "llm"
    MODEL = "gemini-2.0-flash"

    def __init__(self, api_key: str = "", quota_tracker=None, rate_limiter=None):
        self.api_key = api_key
        self.quota_tracker = quota_tracker
        self.rate_limiter = rate_limiter

    def read(
        self,
        image_path: Union[str, Path],
        question: str = "What text does this image contain? Transcribe exactly.",
    ) -> str:
        """
        Call Gemini Vision API to read the image.
        Handles 429 with exponential backoff (2s, 4s, 8s, max 3 retries).
        Returns '[gemini: {error}]' on failure.
        Phase 3 will implement this.
        """
        raise NotImplementedError("Phase 3 — GeminiEngine.read not yet implemented")

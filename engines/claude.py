"""
engines/claude.py — Anthropic Claude Vision wrapper for OCR-Zen.
Model: claude-3-5-haiku-20241022 (free tier, vision capable).
Phase 3 will implement full API call + 429 handling.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union


class ClaudeEngine:
    """
    Calls Anthropic Claude Vision API to read image content.
    Uses claude-3-5-haiku-20241022 (claude-3-opus requires paid tier).
    Phase 3 implementation.
    """

    name = "claude"
    role = "llm"
    MODEL = "claude-3-5-haiku-20241022"

    def __init__(self, api_key: str = "", rate_limiter=None):
        self.api_key = api_key
        self.rate_limiter = rate_limiter

    def read(
        self,
        image_path: Union[str, Path],
        question: str = "What text does this image contain? Transcribe exactly.",
    ) -> str:
        """
        Call Claude Vision API to read the image.
        Handles 429 with exponential backoff (2s, 4s, 8s, max 3 retries).
        Returns '[claude: {error}]' on failure.
        Phase 3 will implement this.
        """
        raise NotImplementedError("Phase 3 — ClaudeEngine.read not yet implemented")

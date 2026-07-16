"""
engines/openai_vision.py — OpenAI GPT-4o Vision wrapper for OCR-Zen.
Model: gpt-4o (requires paid tier — free tier quota will return error).
Phase 3 will implement full API call + 429 handling.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union


class OpenAIVisionEngine:
    """
    Calls OpenAI GPT-4o Vision API to read image content.
    Note: Requires paid tier. Free tier returns [openai: insufficient quota].
    Phase 3 implementation.
    """

    name = "openai"
    role = "llm"
    MODEL = "gpt-4o"

    def __init__(self, api_key: str = "", rate_limiter=None):
        self.api_key = api_key
        self.rate_limiter = rate_limiter

    def read(
        self,
        image_path: Union[str, Path],
        question: str = "What text does this image contain? Transcribe exactly.",
    ) -> str:
        """
        Call GPT-4o Vision API to read the image.
        Returns '[openai: insufficient quota]' if free tier exhausted.
        Phase 3 will implement this.
        """
        raise NotImplementedError("Phase 3 — OpenAIVisionEngine.read not yet implemented")

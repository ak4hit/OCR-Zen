"""
core/tester.py — LLM Vision API test harness for OCR-Zen.
Coordinates calling all available engines on a given image and collecting readings.
Phase 3 will implement the full engine dispatch.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class VisionTester:
    """
    Dispatches an image to all registered engines and returns raw text readings.
    Phase 3 implementation.
    """

    def __init__(self, engines: dict, rate_limiter=None):
        """
        Args:
            engines:      {'name': engine_object} with .read(image_path) method
            rate_limiter: optional RateLimiter instance
        """
        self.engines = engines
        self.rate_limiter = rate_limiter

    def read_all(
        self,
        image_path: Path,
        question: str = "What text does this image contain? Transcribe all text exactly.",
        offline: bool = False,
    ) -> dict[str, str]:
        """
        Read image with all engines. Returns {'engine_name': 'raw_text', ...}.
        Phase 3 will implement this.
        """
        raise NotImplementedError("Phase 3 — VisionTester.read_all not yet implemented")

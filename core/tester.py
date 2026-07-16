"""
core/tester.py — VisionTester: dispatches images to all registered engines.
Phase 3 implementation.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional, Union


class VisionTester:
    """
    Dispatches a single image to all registered engines and collects raw text readings.
    Respects offline mode, rate limiter, and per-engine error handling.
    """

    # Standard question sent to all LLM engines
    DEFAULT_QUESTION = (
        "Transcribe ALL text visible in this image exactly as written. "
        "Include every word, symbol, number, and special character you can see. "
        "Do not describe the image — only output the raw text content."
    )

    def __init__(
        self,
        engines: dict,
        rate_limiter=None,
        rate_limit_seconds: int = 4,
    ):
        """
        Args:
            engines:             {'name': engine_instance} — from EngineRegistry.detect()
            rate_limiter:        Optional Phase-6 RateLimiter instance.
            rate_limit_seconds:  Fallback sleep between API calls if no RateLimiter.
        """
        self.engines             = engines
        self.rate_limiter        = rate_limiter
        self.rate_limit_seconds  = rate_limit_seconds

    def read_all(
        self,
        image_path: Union[str, Path],
        question: Optional[str] = None,
        offline: bool = False,
    ) -> dict[str, str]:
        """
        Read image with all registered engines.

        Args:
            image_path: Path to the adversarial PNG image.
            question:   Custom question for LLM engines (None = DEFAULT_QUESTION).
            offline:    If True, only OCR engines are called (skip LLMs).

        Returns:
            {'engine_name': 'raw_text_reading', ...}
        """
        q       = question or self.DEFAULT_QUESTION
        results = {}
        first_llm_call = True

        for name, engine in self.engines.items():
            role = getattr(engine, "role", "ocr")

            # Skip LLM engines in offline mode
            if offline and role == "llm":
                results[name] = f"[{name}: offline mode — skipped]"
                continue

            try:
                if role == "ocr":
                    # Tesseract / Textract — no question param
                    if name == "tesseract":
                        # Use appropriate pre-processing based on image name
                        img_name = Path(image_path).name
                        preprocess = "red_channel" if "channel_isolation" in img_name else "none"
                        results[name] = engine.read(image_path, preprocess=preprocess)
                    else:
                        results[name] = engine.read(image_path)

                elif role == "llm":
                    # Rate limiting between LLM calls
                    if self.rate_limiter:
                        self.rate_limiter.acquire(name)
                    elif not first_llm_call:
                        # Fallback: simple sleep to avoid hammering APIs
                        time.sleep(self.rate_limit_seconds)

                    results[name]  = engine.read(image_path, question=q)
                    first_llm_call = False

            except Exception as exc:
                results[name] = f"[{name}: unexpected error — {str(exc)[:80]}]"

        return results

    def read_single(
        self,
        image_path: Union[str, Path],
        engine_name: str,
        question: Optional[str] = None,
    ) -> str:
        """
        Read image with a single named engine.
        Returns an error string if engine not registered.
        """
        if engine_name not in self.engines:
            return f"[{engine_name}: not registered]"

        engine = self.engines[engine_name]
        q      = question or self.DEFAULT_QUESTION
        role   = getattr(engine, "role", "ocr")

        try:
            if role == "ocr":
                if engine_name == "tesseract":
                    img_name   = Path(image_path).name
                    preprocess = "red_channel" if "channel_isolation" in img_name else "none"
                    return engine.read(image_path, preprocess=preprocess)
                return engine.read(image_path)
            return engine.read(image_path, question=q)
        except Exception as exc:
            return f"[{engine_name}: {str(exc)[:80]}]"

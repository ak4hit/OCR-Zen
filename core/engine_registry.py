"""
core/engine_registry.py — Engine auto-detection for OCR-Zen.
Discovers which engines are available based on installed packages + .env keys.
Phase 3 will implement full discovery and pretty-printing.
"""

from __future__ import annotations

import shutil
import config


class EngineRegistry:
    """
    Auto-detects available OCR/LLM engines and returns instantiated wrappers.
    Phase 3 implementation.
    """

    def detect(self, offline: bool = False) -> dict:
        """
        Returns dict of {'engine_name': engine_instance} for all available engines.
        Prints availability table. Phase 3 will implement this.
        """
        raise NotImplementedError("Phase 3 — EngineRegistry.detect not yet implemented")

    @staticmethod
    def tesseract_available() -> bool:
        """Quick check: is tesseract binary on PATH?"""
        return shutil.which("tesseract") is not None

    @staticmethod
    def print_availability(engines: dict, skipped: list[str]) -> None:
        """Print the engine availability table. Phase 3 will implement this."""
        raise NotImplementedError("Phase 3 — EngineRegistry.print_availability not yet implemented")

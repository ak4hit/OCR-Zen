"""
core/quota_tracker.py — Daily quota tracker for OCR-Zen.
Persists per-engine daily usage to disk; resets at midnight UTC.
Phase 6 will implement the full tracker.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import config


class QuotaTracker:
    """
    Tracks daily API usage per engine against configured RPD limits.
    Phase 6 implementation.
    """

    _RPD_MAP: dict[str, int] = {
        "gemini": config.GEMINI_RPD,
        "openai": config.OPENAI_RPD,
    }

    def __init__(self, state_file: Path = config.QUOTA_STATE_FILE):
        self.state_file = state_file
        self._state: dict = {}

    def _load(self) -> None:
        """Load state from disk, resetting if a new UTC day has begun."""
        raise NotImplementedError("Phase 6 — QuotaTracker._load not yet implemented")

    def record(self, engine: str, count: int = 1) -> None:
        """Record API calls consumed. Phase 6 implementation."""
        raise NotImplementedError("Phase 6 — QuotaTracker.record not yet implemented")

    def check(self, engine: str) -> tuple[int, int]:
        """Returns (used, limit) for engine. Phase 6 implementation."""
        raise NotImplementedError("Phase 6 — QuotaTracker.check not yet implemented")

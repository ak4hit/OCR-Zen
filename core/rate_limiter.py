"""
core/rate_limiter.py — Token-bucket rate limiter for OCR-Zen.
Enforces per-engine RPM limits from .env config.
Phase 6 will implement the full token-bucket logic.
"""

from __future__ import annotations

import time
import threading

import config


class RateLimiter:
    """
    Per-engine token bucket. Call acquire(engine) before each API request.
    Phase 6 implementation.
    """

    _RPM_MAP: dict[str, int] = {
        "gemini":  config.GEMINI_RPM,
        "claude":  config.CLAUDE_RPM,
        "openai":  config.OPENAI_RPM,
    }

    def __init__(self):
        self._locks: dict[str, threading.Lock] = {}
        self._last_call: dict[str, float] = {}

    def acquire(self, engine: str, extra_wait: float = 0.0) -> None:
        """
        Block until a token is available for the given engine.
        Phase 6 will implement full token-bucket logic.
        """
        raise NotImplementedError("Phase 6 — RateLimiter.acquire not yet implemented")

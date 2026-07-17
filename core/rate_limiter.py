"""
core/rate_limiter.py — Token-bucket rate limiter for OCR-Zen.
Phase 6 implementation: per-engine RPM limiting with verbose logging.
"""

from __future__ import annotations

import threading
import time

import config


class RateLimiter:
    """
    Per-engine token bucket. Call acquire(engine) before each API request.

    Enforces requests-per-minute (RPM) from .env config.
    Thread-safe — safe for concurrent engine calls.

    Usage
    -----
    rl = RateLimiter()
    rl.acquire("gemini")   # blocks if needed, then returns
    gemini.read(image_path)
    """

    _RPM_MAP: dict[str, int] = {
        "gemini":  config.GEMINI_RPM,
        "claude":  config.CLAUDE_RPM,
        "openai":  config.OPENAI_RPM,
    }

    def __init__(self, rpm_overrides: dict[str, int] | None = None):
        """
        Args:
            rpm_overrides: Optional dict to override per-engine RPM.
                           e.g. {"gemini": 5} to slow Gemini to 5 RPM.
        """
        self._rpm: dict[str, int] = dict(self._RPM_MAP)
        if rpm_overrides:
            self._rpm.update(rpm_overrides)

        # Minimum interval between calls = 60 / rpm  seconds
        self._min_interval: dict[str, float] = {
            eng: 60.0 / max(rpm, 1)
            for eng, rpm in self._rpm.items()
        }
        self._last_call: dict[str, float] = {}
        self._locks:     dict[str, threading.Lock] = {
            eng: threading.Lock() for eng in self._rpm
        }

    def acquire(self, engine: str, extra_wait: float = 0.0) -> None:
        """
        Block until a token is available for the given engine.

        Args:
            engine:     Engine name ('gemini', 'claude', 'openai').
            extra_wait: Additional seconds to sleep after the token wait.
                        Use this for --rate-limit CLI flag.
        """
        interval = self._min_interval.get(engine, 0.0) + extra_wait

        if interval <= 0:
            return

        # Ensure a lock exists for unknown engines
        if engine not in self._locks:
            self._locks[engine] = threading.Lock()

        with self._locks[engine]:
            now      = time.monotonic()
            last     = self._last_call.get(engine, 0.0)
            elapsed  = now - last
            wait     = interval - elapsed

            if wait > 0:
                rpm      = self._rpm.get(engine, 0)
                used     = self._usage_this_minute(engine)
                print(
                    f"[Rate Limiter] {engine}: waiting {wait:.1f}s "
                    f"(quota: {used}/{rpm} RPM used)"
                )
                time.sleep(wait)

            self._last_call[engine] = time.monotonic()

    def _usage_this_minute(self, engine: str) -> int:
        """Rough usage count — tracks calls in current minute window."""
        # Simple approximation: seconds elapsed / min_interval
        interval = self._min_interval.get(engine, 1.0)
        last     = self._last_call.get(engine, 0.0)
        elapsed  = time.monotonic() - last
        rpm      = self._rpm.get(engine, 0)
        used     = max(0, int(rpm - (elapsed / 60.0) * rpm))
        return min(used, rpm)

    def available_rpm(self, engine: str) -> int:
        """Return the configured RPM limit for the engine."""
        return self._rpm.get(engine, 0)

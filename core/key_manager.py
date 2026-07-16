"""
core/key_manager.py — Multi-key round-robin key manager for OCR-Zen.
Rotates API keys per engine when quota is exhausted on the current key.
Phase 6 will implement the full rotation logic.
"""

from __future__ import annotations

import config


class KeyManager:
    """
    Cycles through multiple API keys per engine.
    Phase 6 implementation.
    """

    _KEY_POOLS: dict[str, list[str]] = {
        "gemini": config.GOOGLE_API_KEYS,
        "claude": config.ANTHROPIC_API_KEYS,
        "openai": config.OPENAI_API_KEYS,
    }

    def __init__(self):
        self._indices: dict[str, int] = {name: 0 for name in self._KEY_POOLS}

    def get_key(self, engine: str) -> str:
        """Return the current active key for the engine."""
        pool = self._KEY_POOLS.get(engine, [])
        if not pool:
            return ""
        idx = self._indices.get(engine, 0) % len(pool)
        return pool[idx]

    def rotate(self, engine: str) -> str:
        """Rotate to the next key and return it. Phase 6 will log rotation."""
        pool = self._KEY_POOLS.get(engine, [])
        if not pool:
            return ""
        self._indices[engine] = (self._indices.get(engine, 0) + 1) % len(pool)
        new_key = self.get_key(engine)
        idx = self._indices[engine] + 1
        print(f"[KeyManager] {engine}: rotating to key {idx}/{len(pool)}")
        return new_key

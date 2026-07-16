"""
core/divergence.py — Multi-Engine Divergence Scorer for OCR-Zen.
Scores the gap between what OCR engines read vs what LLMs read.
Phase 5 will implement the full scorer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional


def similarity(a: str, b: str) -> float:
    """Normalised similarity score in [0, 1]."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


@dataclass
class EngineScore:
    engine: str
    raw_text: str
    payload_sim: float
    innocent_sim: float
    divergence: float
    role: str        # 'ocr' or 'llm'
    evades: bool     # True when innocent_sim > payload_sim


@dataclass
class DivergenceReport:
    image_path: str
    payload: str
    innocent_text: str
    technique: str
    engines: list[EngineScore] = field(default_factory=list)
    overall_divergence: float = 0.0
    success: bool = False
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class DivergenceScorer:
    """
    Runs every image through all available engines and computes divergence.
    Phase 5 implementation.
    """

    def score(
        self,
        image_path: str,
        payload: str,
        innocent_text: str,
        technique: str,
        engines: dict,   # {'engine_name': callable(image_path) -> str}
        engine_roles: dict,  # {'engine_name': 'ocr'|'llm'}
    ) -> DivergenceReport:
        """
        Score divergence for a single image across all provided engines.
        Phase 5 will implement this.
        """
        raise NotImplementedError("Phase 5 — DivergenceScorer.score not yet implemented")

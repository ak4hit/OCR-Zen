"""
core/calibrator.py — Calibration Engine for OCR-Zen.
Sweeps grey_level × font_size to find optimal rendering parameters.
Phase 4 will implement the full sweep and caching logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CalibrationResult:
    grey_level: int
    font_size: int
    tiny_font_size: int
    score: float
    engine: str
    best_read: str


class Calibrator:
    """
    Sweeps rendering parameters against a target OCR engine to find the
    combination that maximises payload readability while keeping the image
    visually innocent.

    Phase 4 implementation.
    """

    # Pre-seeded Tesseract results from prior testing (Phase 4.2)
    TESSERACT_KNOWN: dict[tuple[int, int], float] = {
        # (grey_level, font_size): similarity_score
        (0, 24): 1.00,   (0, 30): 1.00,   (0, 36): 1.00,   (0, 40): 1.00,
        (50, 24): 1.00,  (50, 30): 1.00,  (50, 36): 1.00,  (50, 40): 1.00,
        (100, 24): 1.00, (100, 30): 1.00, (100, 36): 1.00, (100, 40): 1.00,
        (150, 24): 1.00, (150, 30): 1.00, (150, 36): 1.00, (150, 40): 1.00,
        (180, 24): 0.97, (180, 30): 0.97, (180, 36): 0.95, (180, 40): 0.93,
        (200, 24): 0.95, (200, 30): 0.93,
        (210, 24): 0.91,
        (220, 24): 0.88,
        (230, 24): 0.85,
        # font_size 48 causes line-wrapping — avoid
        (0, 48): 0.84,   (50, 48): 0.83,  (100, 48): 0.82,
    }

    def calibrate(
        self,
        engine_name: str,
        payload: str,
        engine_read_fn,
        force: bool = False,
    ) -> CalibrationResult:
        """
        Run calibration for the given engine.

        If engine_name == 'tesseract', returns pre-seeded result instantly
        unless force=True triggers a full sweep.

        Phase 4 will implement full sweep + cache logic.
        """
        raise NotImplementedError("Phase 4 — Calibrator.calibrate not yet implemented")

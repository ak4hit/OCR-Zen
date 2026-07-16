"""
core/analyzer.py — Result aggregation and scoring for OCR-Zen.
Aggregates DivergenceReports across all techniques into a final run summary.
Phase 5/7 will flesh this out.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.divergence import DivergenceReport


@dataclass
class RunSummary:
    run_id: str
    payload: str
    innocent_text: str
    calibration: dict
    reports: list[DivergenceReport] = field(default_factory=list)
    best_technique: Optional[str] = None
    best_divergence: float = 0.0
    timestamp: str = ""

    def compute_best(self) -> None:
        """Find the technique with the highest overall divergence."""
        if not self.reports:
            return
        best = max(self.reports, key=lambda r: r.overall_divergence)
        self.best_technique = best.technique
        self.best_divergence = best.overall_divergence


class Analyzer:
    """Aggregates technique results into a run summary. Phase 7 implementation."""

    def summarise(self, reports: list[DivergenceReport], **meta) -> RunSummary:
        raise NotImplementedError("Phase 7 — Analyzer.summarise not yet implemented")

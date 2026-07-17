"""
core/analyzer.py — Result aggregation for OCR-Zen.
Phase 7: Analyzer.summarise() builds a RunSummary from DivergenceReports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from core.divergence import DivergenceReport


@dataclass
class RunSummary:
    run_id:          str
    payload:         str
    innocent_text:   str
    calibration:     dict
    reports:         list[DivergenceReport] = field(default_factory=list)
    best_technique:  Optional[str]          = None
    best_divergence: float                  = 0.0
    timestamp:       str                    = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def compute_best(self) -> None:
        """Find the technique with the highest overall divergence."""
        if not self.reports:
            return
        best = max(self.reports, key=lambda r: r.overall_divergence)
        self.best_technique  = best.technique
        self.best_divergence = best.overall_divergence

    def to_dict(self) -> dict:
        self.compute_best()
        return {
            "run_id":         self.run_id,
            "payload":        self.payload,
            "innocent_text":  self.innocent_text,
            "calibration":    self.calibration,
            "techniques":     [r.to_dict() for r in self.reports],
            "best_technique": self.best_technique,
            "best_divergence": round(self.best_divergence, 4),
            "timestamp":      self.timestamp,
        }


class Analyzer:
    """Aggregates technique results into a run summary."""

    def summarise(
        self,
        reports:       list[DivergenceReport],
        run_id:        str  = "",
        payload:       str  = "",
        innocent_text: str  = "",
        calibration:   dict | None = None,
    ) -> RunSummary:
        ts = datetime.now(timezone.utc).isoformat()
        summary = RunSummary(
            run_id        = run_id or f"ocr-zen-{ts[:10]}",
            payload       = payload,
            innocent_text = innocent_text,
            calibration   = calibration or {},
            reports       = reports,
            timestamp     = ts,
        )
        summary.compute_best()
        return summary

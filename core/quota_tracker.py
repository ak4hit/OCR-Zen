"""
core/quota_tracker.py — Daily quota tracker for OCR-Zen.
Phase 6 implementation: persists per-engine daily usage; resets at midnight UTC.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import config


class QuotaTracker:
    """
    Tracks daily API usage per engine against configured RPD limits.

    State is persisted in output/.quota_state.json and resets automatically
    at midnight UTC.

    Usage
    -----
    qt = QuotaTracker()
    qt.record("gemini", count=1)
    used, limit = qt.check("gemini")   # e.g. (42, 1500)
    qt.warn_if_near_limit("gemini")
    """

    _RPD_MAP: dict[str, int] = {
        "gemini": config.GEMINI_RPD,
        "openai": config.OPENAI_RPD,
    }

    WARN_PCT:  float = 0.80   # warn at 80 % consumption
    BLOCK_PCT: float = 1.00   # block at 100 %

    def __init__(self, state_file: Path = config.QUOTA_STATE_FILE):
        self.state_file = state_file
        self._state: dict = {}
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _today_utc(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _load(self) -> None:
        """Load state from disk. Reset if a new UTC day has begun."""
        today = self._today_utc()
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                if data.get("date") == today:
                    self._state = data
                    return
                # New day — reset all counts
                print(f"[Quota] New UTC day ({today}). Resetting all daily quotas.")
            except Exception:
                pass
        # Fresh state
        self._state = {"date": today, "usage": {}}

    def _save(self) -> None:
        """Persist state to disk."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(
                json.dumps(self._state, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            print(f"[Quota] Warning: could not save state: {exc}")

    # ── Public API ────────────────────────────────────────────────────────────

    def record(self, engine: str, count: int = 1) -> None:
        """
        Record API calls consumed by the given engine.

        Args:
            engine: Engine name ('gemini', 'openai', etc.)
            count:  Number of API calls to add (default 1).
        """
        usage = self._state.setdefault("usage", {})
        usage[engine] = usage.get(engine, 0) + count
        self._save()
        self.warn_if_near_limit(engine)

    def check(self, engine: str) -> tuple[int, int]:
        """
        Returns (used, limit) for the engine today.

        Returns (0, 0) for engines without a configured daily limit.
        """
        limit = self._RPD_MAP.get(engine, 0)
        used  = self._state.get("usage", {}).get(engine, 0)
        return used, limit

    def is_exhausted(self, engine: str) -> bool:
        """Return True if the engine has hit its daily quota."""
        used, limit = self.check(engine)
        if limit == 0:
            return False   # no limit configured
        return used >= limit

    def remaining(self, engine: str) -> int:
        """Return how many requests remain today for the engine."""
        used, limit = self.check(engine)
        if limit == 0:
            return 999_999
        return max(0, limit - used)

    def warn_if_near_limit(self, engine: str) -> None:
        """Print a warning if usage is >= WARN_PCT of daily limit."""
        used, limit = self.check(engine)
        if limit == 0:
            return
        pct = used / limit
        if pct >= self.BLOCK_PCT:
            print(
                f"[Quota] {engine}: daily limit reached ({used}/{limit} RPD). "
                f"Use --offline or wait for reset."
            )
        elif pct >= self.WARN_PCT:
            remaining = limit - used
            print(
                f"[Quota] {engine}: {used}/{limit} RPD used "
                f"({pct*100:.0f}%). {remaining} requests remaining today."
            )

    def print_preflight(self, engines: dict) -> None:
        """
        Print the pre-flight quota check table.

        Example
        -------
        [OCR-Zen] Pre-flight check:
          tesseract : available (local)
          claude    : 45/50 RPM available
          gemini    : 1350/1500 RPD used -- 150 requests remaining today
          openai    : quota exhausted -- skipping
        """
        try:
            from rich.console import Console
            from rich.table   import Table
            from rich         import box

            console = Console()
            table   = Table(
                title       = "[bold cyan]OCR-Zen Pre-flight Quota Check[/bold cyan]",
                box         = box.ROUNDED,
                show_header = True,
                header_style= "bold white",
            )
            table.add_column("Engine",  style="cyan",  width=12)
            table.add_column("Status",  width=48)

            for name in engines:
                used, limit = self.check(name)
                if limit == 0:
                    # No daily limit — show RPM only
                    rpm = {"gemini": config.GEMINI_RPM,
                           "claude": config.CLAUDE_RPM,
                           "openai": config.OPENAI_RPM}.get(name, 0)
                    if rpm:
                        status = f"[green]{rpm} RPM available[/green]"
                    else:
                        status = "[green]available (local / unlimited)[/green]"
                elif used >= limit:
                    status = f"[red]quota exhausted ({used}/{limit} RPD) — skipping[/red]"
                elif used / limit >= self.WARN_PCT:
                    status = (
                        f"[yellow]{used}/{limit} RPD used — "
                        f"{limit - used} remaining today[/yellow]"
                    )
                else:
                    status = f"[green]{used}/{limit} RPD used[/green]"
                table.add_row(name, status)

            console.print(table)
            console.print()

        except ImportError:
            print("[OCR-Zen] Pre-flight check:")
            for name in engines:
                used, limit = self.check(name)
                if limit == 0:
                    print(f"  {name:<12}: available")
                else:
                    print(f"  {name:<12}: {used}/{limit} RPD used")

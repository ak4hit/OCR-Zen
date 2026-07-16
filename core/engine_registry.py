"""
core/engine_registry.py — Engine auto-detection and registry for OCR-Zen.
Discovers which engines are available based on .env keys + Tesseract install.
Phase 3 implementation.
"""

from __future__ import annotations

from pathlib import Path

import config


class EngineRegistry:
    """
    Auto-detects available OCR/LLM engines at startup.
    Returns instantiated, ready-to-use engine objects.
    """

    def detect(
        self,
        offline: bool = False,
        rate_limiter=None,
        quota_tracker=None,
    ) -> tuple[dict, list[str]]:
        """
        Detect all available engines.

        Args:
            offline:       If True, only return Tesseract (skip all LLM engines).
            rate_limiter:  Optional RateLimiter instance to inject into engines.
            quota_tracker: Optional QuotaTracker instance for Gemini/OpenAI.

        Returns:
            (engines_dict, skipped_list)
            engines_dict : {'engine_name': engine_instance}
            skipped_list : list of engine names that were skipped and why
        """
        engines: dict  = {}
        skipped: list  = []

        # ── Tesseract (always checked) ─────────────────────────────────────────
        from engines.tesseract import TesseractEngine
        tess = TesseractEngine()
        if self.tesseract_available():
            engines["tesseract"] = tess
        else:
            skipped.append("tesseract (binary not found — install from https://github.com/UB-Mannheim/tesseract/wiki)")

        if offline:
            skipped.extend([
                "gemini  (--offline mode)",
                "claude  (--offline mode)",
                "openai  (--offline mode)",
                "textract(--offline mode)",
            ])
            return engines, skipped

        # ── Gemini ────────────────────────────────────────────────────────────
        from engines.gemini import GeminiEngine
        gemini = GeminiEngine(rate_limiter=rate_limiter, quota_tracker=quota_tracker)
        if gemini.available():
            engines["gemini"] = gemini
        else:
            skipped.append("gemini  (no GOOGLE_API_KEY in .env)")

        # ── Claude ────────────────────────────────────────────────────────────
        from engines.claude import ClaudeEngine
        claude = ClaudeEngine(rate_limiter=rate_limiter)
        if claude.available():
            engines["claude"] = claude
        else:
            skipped.append("claude  (no ANTHROPIC_API_KEY in .env)")

        # ── OpenAI ────────────────────────────────────────────────────────────
        from engines.openai_vision import OpenAIVisionEngine
        openai = OpenAIVisionEngine(rate_limiter=rate_limiter)
        if openai.available():
            engines["openai"] = openai
        else:
            skipped.append("openai  (no OPENAI_API_KEY in .env — paid tier required)")

        # ── Textract (optional) ───────────────────────────────────────────────
        from engines.textract import TextractEngine
        textract = TextractEngine()
        if textract.available():
            engines["textract"] = textract
        else:
            skipped.append("textract(no AWS credentials in .env)")

        return engines, skipped

    @staticmethod
    def tesseract_available() -> bool:
        """Check if the Tesseract binary exists at the configured path."""
        cmd = Path(config.TESSERACT_CMD)
        if cmd.exists():
            return True
        # Also check if it's on PATH
        import shutil
        return shutil.which("tesseract") is not None

    @staticmethod
    def print_availability(engines: dict, skipped: list[str]) -> None:
        """Print the engine availability table to stdout."""
        from rich.console import Console
        from rich.table import Table
        from rich import box

        console = Console()
        table   = Table(
            title   = "[bold cyan]OCR-Zen · Available Engines[/bold cyan]",
            box     = box.ROUNDED,
            show_header=True,
            header_style="bold white",
        )
        table.add_column("Engine",   style="cyan",  width=12)
        table.add_column("Role",     style="white", width=6)
        table.add_column("Status",   style="green", width=32)

        role_map = {
            "tesseract": "ocr",
            "textract":  "ocr",
            "gemini":    "llm",
            "claude":    "llm",
            "openai":    "llm",
        }

        for name, engine in engines.items():
            role = getattr(engine, "role", role_map.get(name, "?"))
            table.add_row(name, role, "[green]AVAILABLE[/green]")

        for reason in skipped:
            name   = reason.split("(")[0].strip()
            detail = reason[reason.find("("):] if "(" in reason else ""
            table.add_row(name, role_map.get(name, "?"), f"[dim]SKIPPED {detail}[/dim]")

        console.print(table)
        console.print()

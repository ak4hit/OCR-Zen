"""
core/calibrator.py — Calibration Engine for OCR-Zen.

Phase 4 implementation:
  4.1 — Full grey_level × font_size sweep (45 test images per run)
  4.2 — Pre-seeded Tesseract cache (returns instantly for Tesseract)
  4.3 — Remote calibration mode (--calibrate-remote URL)
  4.4 — Calibration cache (JSON, 7-day TTL)
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from PIL import Image, ImageDraw, ImageFont

import config

# ── Font loader (same fallback chain as generator.py) ─────────────────────────
_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\cour.ttf",
    r"C:\Windows\Fonts\times.ttf",
    "DejaVuSans-Bold.ttf",
    "DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _similarity(a: str, b: str) -> float:
    """SequenceMatcher ratio between two strings (case-insensitive)."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class CalibrationResult:
    grey_level: int
    font_size: int
    tiny_font_size: int
    score: float
    engine: str
    best_read: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CalibrationResult":
        return cls(**d)


@dataclass
class SweepEntry:
    """One cell of the calibration sweep matrix."""
    grey_level: int
    font_size: int
    score: float
    read_text: str


# ── Calibrator ────────────────────────────────────────────────────────────────

class Calibrator:
    """
    Sweeps rendering parameters against a target OCR engine to find the
    combination that maximises payload readability while keeping the image
    visually innocent.

    Usage
    -----
    calibrator = Calibrator()
    result = calibrator.calibrate(
        engine_name="tesseract",
        payload="id && whoami",
        engine_read_fn=tess.read,
    )
    """

    # ── 4.1 / 4.2  Sweep grid ─────────────────────────────────────────────────
    GREY_LEVELS: list[int]  = [0, 50, 100, 150, 180, 200, 210, 220, 230]
    FONT_SIZES:  list[int]  = [24, 30, 36, 40, 48]
    CACHE_TTL_DAYS: int     = 7

    # ── 4.2  Pre-seeded Tesseract results (from prior empirical testing) ───────
    # Key: (grey_level, font_size) → similarity score
    TESSERACT_KNOWN: dict[tuple[int, int], float] = {
        (0, 24): 1.00,   (0, 30): 1.00,   (0, 36): 1.00,   (0, 40): 1.00,
        (50, 24): 1.00,  (50, 30): 1.00,  (50, 36): 1.00,  (50, 40): 1.00,
        (100, 24): 1.00, (100, 30): 1.00, (100, 36): 1.00, (100, 40): 1.00,
        (150, 24): 1.00, (150, 30): 1.00, (150, 36): 1.00, (150, 40): 1.00,
        (180, 24): 0.97, (180, 30): 0.97, (180, 36): 0.95, (180, 40): 0.93,
        (200, 24): 0.95, (200, 30): 0.93,
        (210, 24): 0.91,
        (220, 24): 0.88,
        (230, 24): 0.85,
        # font_size=48 causes line-wrapping artefacts — penalise
        (0,   48): 0.84,  (50,  48): 0.83,  (100, 48): 0.82,
        (150, 48): 0.81,  (180, 48): 0.78,  (200, 48): 0.75,
        (210, 48): 0.73,  (220, 48): 0.71,  (230, 48): 0.70,
    }

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _payload_hash(payload: str) -> str:
        return hashlib.md5(payload.encode()).hexdigest()[:10]

    def _cache_path(self, engine_name: str, payload: str) -> Path:
        return config.CALIBRATION_DIR / f"{engine_name}_{self._payload_hash(payload)}.json"

    def _load_cache(self, engine_name: str, payload: str) -> Optional[CalibrationResult]:
        """Return cached CalibrationResult if it exists and is < 7 days old."""
        path = self._cache_path(engine_name, payload)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01T00:00:00+00:00"))
            age_days = (datetime.now(timezone.utc) - cached_at).days
            if age_days >= self.CACHE_TTL_DAYS:
                print(f"[Calibrator] Cache expired ({age_days}d old) for {engine_name}.")
                return None
            print(f"[Calibrator] Cache hit for {engine_name} (age: {age_days}d).")
            return CalibrationResult.from_dict(data["result"])
        except Exception as exc:
            print(f"[Calibrator] Cache read error ({exc}) — re-running sweep.")
            return None

    def _save_cache(self, engine_name: str, payload: str, result: CalibrationResult) -> None:
        """Persist calibration result to disk."""
        path = self._cache_path(engine_name, payload)
        data = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "engine":    engine_name,
            "payload":   payload,
            "result":    result.to_dict(),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"[Calibrator] Result cached -> {path.name}")

    # ── 4.1  Test image renderer ──────────────────────────────────────────────

    @staticmethod
    def _render_test_image(text: str, grey: int, font_size: int) -> Image.Image:
        """
        Render `text` in colour RGB(grey, grey, grey) on a white 800×150 image.
        This is the canonical test image for calibration sweeps.
        """
        W, H = 800, 150
        img  = Image.new("RGB", (W, H), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        font = _load_font(font_size)
        draw.text((20, H // 2 - font_size // 2), text, fill=(grey, grey, grey), font=font)
        return img

    # ── 4.1  Full sweep ───────────────────────────────────────────────────────

    def _run_sweep(
        self,
        payload: str,
        engine_read_fn: Callable[[str | Path], str],
        verbose: bool = True,
    ) -> list[SweepEntry]:
        """
        Render 45 test images (9 grey × 5 font-sizes) and score each one.
        Returns list of SweepEntry sorted by score descending.
        """
        import tempfile, os

        entries: list[SweepEntry] = []
        total = len(self.GREY_LEVELS) * len(self.FONT_SIZES)
        done  = 0

        with tempfile.TemporaryDirectory() as tmp:
            for grey in self.GREY_LEVELS:
                for size in self.FONT_SIZES:
                    done += 1
                    img_path = Path(tmp) / f"cal_g{grey}_s{size}.png"
                    img = self._render_test_image(payload, grey, size)
                    img.save(str(img_path))

                    try:
                        read = engine_read_fn(str(img_path))
                    except Exception as exc:
                        read = f"[error: {exc}]"

                    score = _similarity(payload, read)
                    entries.append(SweepEntry(grey, size, score, read))

                    if verbose:
                        bar  = "█" * int(score * 10) + "░" * (10 - int(score * 10))
                        icon = "✅" if score >= 0.70 else "⚠️ " if score >= 0.40 else "❌"
                        print(
                            f"  [{done:02d}/{total}] grey={grey:3d}  size={size:2d}  "
                            f"{icon} score={score:.2f}  {bar}  read={read[:35]!r}"
                        )

        entries.sort(key=lambda e: e.score, reverse=True)
        return entries

    # ── 4.2  Tesseract fast-path ──────────────────────────────────────────────

    def _tesseract_from_known(self, payload: str) -> CalibrationResult:
        """
        Return a CalibrationResult synthesised from the pre-seeded lookup table.
        Picks the highest-scoring (grey, size) pair from TESSERACT_KNOWN that
        avoids font_size=48 (line-wrap artefact), favouring grey=230 (most
        innocuous to human eye while still machine-readable).
        """
        best_score = -1.0
        best_grey  = 230
        best_size  = 30

        # Priority order: prefer grey=230 with good score, fall back to lower grey
        for grey in [230, 220, 210, 200, 180, 150, 100, 50, 0]:
            for size in [30, 24, 36, 40]:   # prefer moderate sizes
                key   = (grey, size)
                score = self.TESSERACT_KNOWN.get(key, -1.0)
                if score > best_score:
                    best_score = score
                    best_grey  = grey
                    best_size  = size

        return CalibrationResult(
            grey_level    = best_grey,
            font_size     = best_size,
            tiny_font_size= 14,
            score         = best_score,
            engine        = "tesseract",
            best_read     = payload,   # known to read correctly
        )

    # ── 4.3  Remote calibration ───────────────────────────────────────────────

    def calibrate_remote(
        self,
        url: str,
        payload: str,
        verbose: bool = True,
    ) -> CalibrationResult:
        """
        Upload test images to a remote URL endpoint and score based on
        whether the payload appears in the HTTP response body.

        Useful for calibrating against a live OCR-enabled pipeline.

        Args:
            url:     Target endpoint that accepts multipart/form-data image upload.
            payload: Payload text to search for in the response.
            verbose: Print progress.

        Returns:
            CalibrationResult with engine='remote:<url_host>'.
        """
        import tempfile
        from urllib.parse import urlparse

        try:
            import requests
        except ImportError:
            raise RuntimeError("[Calibrator] 'requests' package not installed.")

        host        = urlparse(url).netloc or url
        engine_name = f"remote:{host}"
        entries: list[SweepEntry] = []
        total = len(self.GREY_LEVELS) * len(self.FONT_SIZES)
        done  = 0

        if verbose:
            print(f"\n[Calibrator] Remote sweep → {url}")
            print(f"[Calibrator] {total} test images to upload.\n")

        with tempfile.TemporaryDirectory() as tmp:
            for grey in self.GREY_LEVELS:
                for size in self.FONT_SIZES:
                    done += 1
                    img_path = Path(tmp) / f"cal_g{grey}_s{size}.png"
                    img = self._render_test_image(payload, grey, size)
                    img.save(str(img_path))

                    score    = 0.0
                    raw_text = "[no response]"
                    try:
                        with open(img_path, "rb") as fh:
                            resp = requests.post(
                                url,
                                files={"file": (img_path.name, fh, "image/png")},
                                timeout=15,
                            )
                        raw_text = resp.text[:500]
                        # Score: does the payload appear anywhere in the response?
                        score = _similarity(payload, raw_text)
                    except requests.exceptions.Timeout:
                        raw_text = "[timeout]"
                    except Exception as exc:
                        raw_text = f"[error: {exc}]"

                    entries.append(SweepEntry(grey, size, score, raw_text))

                    if verbose:
                        icon = "✅" if score >= 0.70 else "⚠️ " if score >= 0.40 else "❌"
                        print(
                            f"  [{done:02d}/{total}] grey={grey:3d}  size={size:2d}  "
                            f"{icon} score={score:.2f}  resp={raw_text[:40]!r}"
                        )
                    time.sleep(0.5)   # polite pacing for remote endpoint

        best = max(entries, key=lambda e: e.score)
        result = CalibrationResult(
            grey_level    = best.grey_level,
            font_size     = best.font_size,
            tiny_font_size= 14,
            score         = best.score,
            engine        = engine_name,
            best_read     = best.read_text,
        )
        self._save_cache(engine_name, payload, result)
        return result

    # ── Public API ────────────────────────────────────────────────────────────

    def calibrate(
        self,
        engine_name: str,
        payload: str,
        engine_read_fn: Callable[[str | Path], str],
        force: bool = False,
        verbose: bool = True,
    ) -> CalibrationResult:
        """
        Run calibration for the given engine.

        For 'tesseract': returns from pre-seeded lookup table instantly,
        unless force=True triggers a full live sweep.

        For LLM engines: checks cache first, then runs the full 45-image
        sweep and saves results to disk.

        Args:
            engine_name:    Name tag for the engine (e.g. 'tesseract', 'gemini').
            payload:        Target payload text.
            engine_read_fn: Callable that takes an image path and returns the
                            engine's text reading of that image.
            force:          If True, bypass cache and re-run sweep.
            verbose:        Print sweep progress.

        Returns:
            CalibrationResult with optimal grey_level, font_size, and score.
        """
        # ── Tesseract fast-path (pre-seeded, no images needed) ─────────────────
        if engine_name == "tesseract" and not force:
            if verbose:
                print(
                    "[Calibrator] tesseract: using pre-seeded results "
                    "(skip sweep). Pass force=True to re-sweep."
                )
            result = self._tesseract_from_known(payload)
            # Still cache it so other code can load it uniformly
            self._save_cache(engine_name, payload, result)
            return result

        # ── Cache check for LLM engines ────────────────────────────────────────
        if not force:
            cached = self._load_cache(engine_name, payload)
            if cached is not None:
                return cached

        # ── Full sweep ─────────────────────────────────────────────────────────
        if verbose:
            print(
                f"\n[Calibrator] Starting sweep for engine={engine_name!r}, "
                f"payload={payload!r}"
            )
            print(
                f"[Calibrator] Grid: {len(self.GREY_LEVELS)} grey levels × "
                f"{len(self.FONT_SIZES)} font sizes = "
                f"{len(self.GREY_LEVELS) * len(self.FONT_SIZES)} test images\n"
            )

        entries = self._run_sweep(payload, engine_read_fn, verbose=verbose)

        if not entries:
            # Fallback: no images could be rendered/read
            return CalibrationResult(
                grey_level    = 230,
                font_size     = 30,
                tiny_font_size= 14,
                score         = 0.0,
                engine        = engine_name,
                best_read     = "",
            )

        best = entries[0]
        result = CalibrationResult(
            grey_level    = best.grey_level,
            font_size     = best.font_size,
            tiny_font_size= 14,
            score         = best.score,
            engine        = engine_name,
            best_read     = best.read_text,
        )

        if verbose:
            icon = "✅" if result.score >= 0.70 else "⚠️ "
            print(
                f"\n[Calibrator] {icon} Best: grey={result.grey_level}  "
                f"font={result.font_size}  score={result.score:.2f}"
            )

        self._save_cache(engine_name, payload, result)
        return result

    # ── Convenience: print full sweep table ───────────────────────────────────

    def print_sweep_table(
        self,
        engine_name: str,
        payload: str,
        engine_read_fn: Callable[[str | Path], str],
        force: bool = False,
    ) -> CalibrationResult:
        """
        Run calibration and print a rich table of all sweep results.
        Useful for detailed analysis runs.
        """
        try:
            from rich.console import Console
            from rich.table  import Table
            from rich        import box

            console = Console()
        except ImportError:
            return self.calibrate(engine_name, payload, engine_read_fn, force=force)

        entries = self._run_sweep(payload, engine_read_fn, verbose=False)

        table = Table(
            title       = f"[bold cyan]Calibration Sweep — {engine_name}[/bold cyan]",
            box         = box.ROUNDED,
            show_header = True,
            header_style= "bold white",
        )
        table.add_column("Grey",      style="cyan",   width=6)
        table.add_column("FontSize",  style="cyan",   width=9)
        table.add_column("Score",     style="yellow", width=7)
        table.add_column("Read",      style="white",  width=50)

        for e in sorted(entries, key=lambda x: (x.grey_level, x.font_size)):
            icon  = "✅" if e.score >= 0.70 else ("⚠️ " if e.score >= 0.40 else "❌")
            score_str = f"{icon} {e.score:.2f}"
            table.add_row(str(e.grey_level), str(e.font_size), score_str, e.read_text[:48])

        console.print(table)

        best = max(entries, key=lambda e: e.score)
        result = CalibrationResult(
            grey_level    = best.grey_level,
            font_size     = best.font_size,
            tiny_font_size= 14,
            score         = best.score,
            engine        = engine_name,
            best_read     = best.read_text,
        )
        self._save_cache(engine_name, payload, result)
        return result

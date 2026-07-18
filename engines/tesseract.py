"""
engines/tesseract.py — Local Tesseract OCR wrapper for OCR-Zen.
Phase 2/3 implementation. On Windows, set TESSERACT_CMD in .env if needed.

Supports two modes:
  1. pytesseract  — preferred; install with: pip install pytesseract
  2. subprocess   — automatic fallback when pytesseract is not available
                    (works on Kali/Debian "externally-managed" environments
                    where pip is restricted but the tesseract binary is present)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Union

from PIL import Image, ImageOps

import config

# ── Backend detection ─────────────────────────────────────────────────────────
#
# Priority:
#   1. pytesseract  (rich API, direct PIL integration)
#   2. subprocess   (no Python package needed — calls tesseract binary directly)
#   3. unavailable  (neither works)

_USE_SUBPROCESS = False   # True  → use subprocess path
_AVAILABLE      = False   # False → return error string immediately

try:
    import pytesseract
    # Point pytesseract at the configured binary path (Windows mainly)
    if config.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
    _AVAILABLE = True

except ImportError:
    # pytesseract not installed (e.g. Kali pip restrictions).
    # Fall back to calling the tesseract binary directly via subprocess.
    _tess_cmd = config.TESSERACT_CMD or "tesseract"
    _on_path   = shutil.which("tesseract") is not None
    _explicit  = bool(config.TESSERACT_CMD and os.path.exists(config.TESSERACT_CMD))

    if _on_path or _explicit:
        _AVAILABLE      = True
        _USE_SUBPROCESS = True
        print(
            "[TesseractEngine] pytesseract not installed — "
            "using subprocess fallback (tesseract binary on PATH)."
        )
    else:
        _AVAILABLE = False


# ── Engine ────────────────────────────────────────────────────────────────────

class TesseractEngine:
    """
    Wraps Tesseract for local OCR with pre-processing options.

    Uses pytesseract when available; automatically falls back to direct
    subprocess execution when pytesseract is not installed (e.g. Kali Linux
    with externally-managed pip environment).

    Gracefully returns an error string starting with '[' on all failures.
    """

    name = "tesseract"
    role = "ocr"

    def read(
        self,
        image_path: Union[str, Path],
        psm: int = 6,
        preprocess: str = "none",
    ) -> str:
        """
        Run Tesseract OCR on the given image.

        Args:
            image_path:  Path to the PNG/JPEG image.
            psm:         Page segmentation mode.
                           6 = single uniform block of text (default)
                          11 = sparse text, no specific order
                           3 = auto (no OSD)
            preprocess:  'none' | 'greyscale' | 'threshold' | 'red_channel'
                         Use 'red_channel' for the channel_isolation technique.

        Returns:
            Extracted text string, or an error string starting with '['.
        """
        if not _AVAILABLE:
            return (
                "[tesseract: not available — install pytesseract "
                "(pip install pytesseract) or ensure tesseract binary is on PATH]"
            )

        try:
            img = Image.open(str(image_path)).convert("RGB")

            # ── Pre-processing ─────────────────────────────────────────────────
            if preprocess == "greyscale":
                img = img.convert("L")

            elif preprocess == "threshold":
                # Hard binary threshold — maximises contrast for faint text
                img = img.convert("L").point(lambda x: 0 if x < 200 else 255, "1")

            elif preprocess == "red_channel":
                # channel_isolation technique: payload color is (255, red_shade, red_shade)
                # where red_shade < 255 (e.g. 210).  Background is pure white (255, 255, 255).
                #
                # Green channel contrast:
                #   background pixel G = 255
                #   payload text     G = red_shade (e.g. 210)  -> contrast = 45
                #
                # Strategy: extract green channel -> apply binary threshold at 240.
                # Pixels with G < 240 (payload text) -> black (0)  = dark text
                # Pixels with G >= 240 (background)  -> white (255) = white bg
                # Result: dark text on white background — Tesseract's preferred input.
                _, g, _ = img.split()
                img = g.point(lambda p: 0 if p < 240 else 255, "1")

            # ── OCR dispatch ───────────────────────────────────────────────────
            if _USE_SUBPROCESS:
                return self._read_subprocess(img, psm)

            cfg  = f"--psm {psm} --oem 3"
            text = pytesseract.image_to_string(img, config=cfg)
            return text.strip()

        except FileNotFoundError as exc:
            if str(image_path) in str(exc):
                return f"[tesseract: image not found: {image_path}]"
            return "[tesseract not installed — check TESSERACT_CMD in .env]"
        except Exception as exc:
            msg = str(exc)
            if "tesseract" in msg.lower() and ("not found" in msg.lower() or "not installed" in msg.lower()):
                return "[tesseract not installed — check TESSERACT_CMD in .env]"
            return f"[tesseract error: {exc}]"

    # ── Subprocess backend ────────────────────────────────────────────────────

    def _read_subprocess(self, img: Image.Image, psm: int) -> str:
        """
        Call tesseract binary directly via subprocess.
        Used when pytesseract is not installed.

        Saves the (possibly pre-processed) PIL image to a temp file,
        runs: tesseract <tmp.png> stdout --psm <psm> --oem 3
        then deletes the temp file.
        """
        cmd      = config.TESSERACT_CMD or "tesseract"
        tmp_path = None
        try:
            # Write pre-processed image to a temp PNG
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            # Convert 1-bit images to L for saving as PNG without palette issues
            save_img = img.convert("L") if img.mode == "1" else img
            save_img.save(tmp_path, "PNG")

            result = subprocess.run(
                [cmd, tmp_path, "stdout", "--psm", str(psm), "--oem", "3"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Non-zero exit sometimes still has useful stdout; check stderr for hard errors
            if result.returncode != 0 and not result.stdout.strip():
                err = result.stderr.strip()[:120]
                return f"[tesseract error (rc={result.returncode}): {err}]"
            return result.stdout.strip()

        except FileNotFoundError:
            return (
                f"[tesseract: binary '{cmd}' not found — "
                "install with: sudo apt install tesseract-ocr]"
            )
        except subprocess.TimeoutExpired:
            return "[tesseract: timeout (>30s)]"
        except Exception as exc:
            return f"[tesseract error: {exc}]"
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

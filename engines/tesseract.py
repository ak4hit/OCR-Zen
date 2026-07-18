"""
engines/tesseract.py — Local Tesseract OCR wrapper for OCR-Zen.
Phase 2/3 implementation. On Windows, set TESSERACT_CMD in .env if needed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from PIL import Image, ImageOps

import config

# ── Tesseract binary path ─────────────────────────────────────────────────────
try:
    import pytesseract
    # Point pytesseract to the confirmed install location
    if config.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


class TesseractEngine:
    """
    Wraps pytesseract for local OCR with pre-processing options.
    Gracefully returns an error string if Tesseract is not installed.
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
            return "[tesseract: pytesseract not installed]"

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
                #   payload text    G = red_shade (e.g. 210)  → contrast = 45
                #
                # Strategy: extract green channel → apply binary threshold at 240.
                # Pixels with G < 240 (the payload text) → become black (0).
                # Pixels with G >= 240 (the background)  → become white (255).
                # Result: dark text on white background — Tesseract's preferred input.
                _, g, _ = img.split()
                img = g.point(lambda p: 0 if p < 240 else 255, "1")

            # ── OCR ────────────────────────────────────────────────────────────
            cfg = f"--psm {psm} --oem 3"
            text = pytesseract.image_to_string(img, config=cfg)
            return text.strip()

        except pytesseract.pytesseract.TesseractNotFoundError:
            return "[tesseract not installed — check TESSERACT_CMD in .env]"
        except FileNotFoundError:
            return f"[tesseract: image not found: {image_path}]"
        except Exception as exc:
            return f"[tesseract error: {exc}]"

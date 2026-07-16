"""
engines/tesseract.py — Local Tesseract OCR wrapper for OCR-Zen.
Phase 2/3 implementation — Tesseract confirmed at C:\Program Files\Tesseract-OCR\.
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
                # channel_isolation technique: extract green channel (payload
                # is in red — (255, red_shade, red_shade) — green channel has
                # contrast between text and background), then invert so payload
                # appears dark on light for Tesseract.
                _, g, _ = img.split()
                img = ImageOps.invert(g)

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

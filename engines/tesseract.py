"""
engines/tesseract.py — Local Tesseract OCR wrapper for OCR-Zen.
Phase 3 will implement full PSM/DPI/pre-processing options.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union


class TesseractEngine:
    """
    Wraps pytesseract for local OCR. Gracefully handles missing installation.
    Phase 3 implementation.
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
            image_path: Path to the PNG/JPEG image.
            psm:        Tesseract page segmentation mode (6=single block, 11=sparse, 3=auto).
            preprocess: 'none' | 'greyscale' | 'threshold' | 'red_channel'

        Returns:
            Extracted text string, or '[tesseract not installed]' if missing.

        Phase 3 will implement this fully.
        """
        raise NotImplementedError("Phase 3 — TesseractEngine.read not yet implemented")

"""
engines/textract.py — AWS Textract wrapper for OCR-Zen (optional).
Only initialises if AWS credentials are present in .env.
Phase 3 will implement full API call.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import config


class TextractEngine:
    """
    Calls AWS Textract to detect document text in an image.
    Only available when AWS_ACCESS_KEY_ID is configured in .env.
    Phase 3 implementation.
    """

    name = "textract"
    role = "ocr"

    def __init__(self):
        self.available = bool(config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY)

    def read(self, image_path: Union[str, Path]) -> str:
        """
        Call AWS Textract detect_document_text API.
        Returns '[textract: no credentials]' if not configured.
        Phase 3 will implement this.
        """
        if not self.available:
            return "[textract: no credentials]"
        raise NotImplementedError("Phase 3 — TextractEngine.read not yet implemented")

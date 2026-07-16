"""
engines/textract.py — AWS Textract wrapper for OCR-Zen (optional).
Only initialises when AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY are in .env.
Phase 3 implementation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import config


class TextractEngine:
    """
    Calls AWS Textract detect_document_text API to extract text from an image.
    Silently skipped if AWS credentials are not configured.
    """

    name = "textract"
    role = "ocr"

    def __init__(self):
        self._client    = None
        self.available_ = bool(config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY)

    def available(self) -> bool:
        return self.available_

    def _get_client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client(
                "textract",
                region_name          = config.AWS_REGION,
                aws_access_key_id    = config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key= config.AWS_SECRET_ACCESS_KEY,
            )
        return self._client

    def read(self, image_path: Union[str, Path]) -> str:
        """
        Call AWS Textract detect_document_text.
        Returns '[textract: no credentials]' if not configured.
        Returns '[textract: {error}]' on API failure.
        """
        if not self.available_:
            return "[textract: no credentials]"

        try:
            with open(str(image_path), "rb") as f:
                image_bytes = f.read()

            client   = self._get_client()
            response = client.detect_document_text(
                Document={"Bytes": image_bytes}
            )

            lines = [
                block["Text"]
                for block in response.get("Blocks", [])
                if block.get("BlockType") == "LINE"
            ]
            return "\n".join(lines).strip()

        except Exception as exc:
            return f"[textract: {str(exc)[:120]}]"

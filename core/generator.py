"""
core/generator.py — Adversarial Image Generator for OCR-Zen.
Implements all steganographic image generation techniques.
Phase 2 will flesh out each technique fully.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

import config

# ── Font resolution ───────────────────────────────────────────────────────────
_FONT_CANDIDATES = [
    "DejaVuSans-Bold.ttf",
    "DejaVuSans.ttf",
    "arial.ttf",
    "Arial.ttf",
    "LiberationSans-Regular.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a TTF font; fall back to PIL default if none found."""
    for name in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


# ── Technique registry ────────────────────────────────────────────────────────
class AdversarialImageGenerator:
    """Generates adversarial images using various steganographic techniques."""

    TECHNIQUES: list[str] = [
        "color_manipulation",
        "texture_overlay",
        "ambiguous_text",
        "context_hijacking",
        "font_trickery",
        "channel_isolation",
        "resolution_split",
    ]

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or config.IMAGES_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        payload: str,
        innocent_text: str,
        technique: str,
        calibration: Optional[dict] = None,
    ) -> tuple[Path, str]:
        """
        Generate an adversarial image.

        Args:
            payload:       The hidden OCR-readable payload.
            innocent_text: The visible innocent text humans see.
            technique:     One of TECHNIQUES.
            calibration:   Optional dict with 'grey_level', 'font_size', etc.

        Returns:
            (image_path, technique) tuple.
        """
        if technique not in self.TECHNIQUES:
            raise ValueError(f"Unknown technique: {technique!r}. Choose from {self.TECHNIQUES}")

        cal = calibration or {}
        method = getattr(self, f"_technique_{technique}")
        img: Image.Image = method(payload, innocent_text, cal)

        out_path = self.output_dir / f"adversarial_{technique}.png"
        img.save(str(out_path), "PNG", dpi=(300, 300))
        return out_path, technique

    # ── Technique stubs (implemented in Phase 2) ──────────────────────────────

    def _technique_color_manipulation(
        self, payload: str, innocent: str, cal: dict
    ) -> Image.Image:
        """Phase 2.2 — Payload hidden as near-white text below visible content."""
        raise NotImplementedError("Phase 2 — color_manipulation not yet implemented")

    def _technique_texture_overlay(
        self, payload: str, innocent: str, cal: dict
    ) -> Image.Image:
        """Phase 2.3 — Payload rendered as subtle per-character jitter overlay."""
        raise NotImplementedError("Phase 2 — texture_overlay not yet implemented")

    def _technique_ambiguous_text(
        self, payload: str, innocent: str, cal: dict
    ) -> Image.Image:
        """Phase 2.4 — Cyrillic/Unicode homoglyphs that fool text filters."""
        raise NotImplementedError("Phase 2 — ambiguous_text not yet implemented")

    def _technique_context_hijacking(
        self, payload: str, innocent: str, cal: dict
    ) -> Image.Image:
        """Phase 2.5 — Payload embedded as low-contrast 'internal note' in a document."""
        raise NotImplementedError("Phase 2 — context_hijacking not yet implemented")

    def _technique_font_trickery(
        self, payload: str, innocent: str, cal: dict
    ) -> Image.Image:
        """Phase 2.6 — Payload at tiny font size (14px) saved at 300 DPI."""
        raise NotImplementedError("Phase 2 — font_trickery not yet implemented")

    def _technique_channel_isolation(
        self, payload: str, innocent: str, cal: dict
    ) -> Image.Image:
        """Phase 2.7 — Payload encoded in red channel only; humans see pink tint."""
        raise NotImplementedError("Phase 2 — channel_isolation not yet implemented")

    def _technique_resolution_split(
        self, payload: str, innocent: str, cal: dict
    ) -> Image.Image:
        """Phase 2.8 — Payload visible only at full OCR resolution, not thumbnail."""
        raise NotImplementedError("Phase 2 — resolution_split not yet implemented")

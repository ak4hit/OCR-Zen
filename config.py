"""
config.py — Configuration loader for OCR-Zen.
Reads from .env file and exposes typed config values throughout the project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent / ".env")

# ── API Keys ──────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")

# ── Multi-key round-robin support ─────────────────────────────────────────────
def _collect_keys(prefix: str) -> list[str]:
    """Collect GOOGLE_API_KEY_1, _2, _3 ... style multi-keys."""
    keys = []
    i = 1
    while True:
        key = os.getenv(f"{prefix}_{i}", "")
        if not key:
            break
        keys.append(key)
        i += 1
    # Fall back to the base key if no numbered ones found
    base = os.getenv(prefix, "")
    if not keys and base:
        keys.append(base)
    return keys

GOOGLE_API_KEYS: list[str] = _collect_keys("GOOGLE_API_KEY")
ANTHROPIC_API_KEYS: list[str] = _collect_keys("ANTHROPIC_API_KEY")
OPENAI_API_KEYS: list[str] = _collect_keys("OPENAI_API_KEY")

# ── Rate Limits ───────────────────────────────────────────────────────────────
GEMINI_RPM: int = int(os.getenv("GEMINI_RPM", "12"))
CLAUDE_RPM: int = int(os.getenv("CLAUDE_RPM", "50"))
OPENAI_RPM: int = int(os.getenv("OPENAI_RPM", "20"))

# ── Daily Quotas ──────────────────────────────────────────────────────────────
GEMINI_RPD: int = int(os.getenv("GEMINI_RPD", "1500"))
OPENAI_RPD: int = int(os.getenv("OPENAI_RPD", "200"))

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR: Path = Path(__file__).parent
OUTPUT_DIR: Path = ROOT_DIR / "output"
IMAGES_DIR: Path = OUTPUT_DIR / "images"
REPORTS_DIR: Path = OUTPUT_DIR / "reports"
CALIBRATION_DIR: Path = OUTPUT_DIR / "calibration"
WORDLISTS_DIR: Path = ROOT_DIR / "wordlists"
QUOTA_STATE_FILE: Path = OUTPUT_DIR / ".quota_state.json"

# Ensure output directories exist
for _dir in [IMAGES_DIR, REPORTS_DIR, CALIBRATION_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

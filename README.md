# OCR-Zen 🔮

![OCR-Zen Banner](assets/ocr_zen_banner.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-cyan.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Security Research](https://img.shields.io/badge/purpose-security%20research-red.svg)]()

> **The opposite of a CAPTCHA.**
>
> Generates images that humans read as innocent text — but OCR engines and document-processing pipelines read as shell commands or payloads.

**Author**: [ak4hit](https://github.com/ak4hit)
**Type**: Offensive Security / Red Team Research
**Core Engine**: Tesseract OCR + Multi-LLM Vision API Testing

---

## What Is OCR-Zen?

A CAPTCHA generates images that humans can read but machines cannot.

**OCR-Zen generates images that machines read as payloads but humans read as innocent text.**

Primary use cases:
- Bypassing **content filters**, **WAFs**, and **DLP tools** that scan extracted text
- Testing **AI document pipelines** (invoice processors, contract parsers) for prompt injection via image
- **Red team assessments** where documents are OCR'd before being processed

---

## Install

```bash
# 1. Clone the repo
git clone https://github.com/ak4hit/OCR-Zen
cd OCR-Zen

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install Tesseract (required for local OCR)
# Ubuntu/Debian:
sudo apt install tesseract-ocr tesseract-ocr-eng

# macOS:
brew install tesseract

# Windows: https://github.com/UB-Mannheim/tesseract/wiki

# 4. Copy .env and add your API keys (all optional -- works offline with Tesseract)
cp .env.example .env
```

---

## Quick Start

```bash
# Offline mode (Tesseract only, no API keys needed)
python main.py --offline

# With a custom payload (supply your own at runtime)
python main.py --payload "id && whoami" --innocent "Invoice #1234" --offline

# Test all techniques and score divergence (needs API keys in .env)
python main.py --payload "id && whoami" --techniques all

# Batch mode from wordlist
python main.py --payload-file wordlists/shell_commands.txt --offline

# HTML + JSON report
python main.py --offline --format both
```

---

## CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--payload TEXT` | `id && whoami` | Payload to hide in image |
| `--innocent TEXT` | `Invoice #1234 - Total: $500` | Visible cover text |
| `--techniques TEXT` | `all` | Comma-separated list or `all` |
| `--engine TEXT` | `tesseract` | Engine for calibration |
| `--offline` | off | Tesseract only, no API calls |
| `--calibrate-remote URL` | -- | Calibrate against a live target endpoint |
| `--skip-calibration` | off | Use defaults, skip parameter sweep |
| `--skip-divergence` | off | Skip multi-engine scoring |
| `--rate-limit INT` | `4` | Seconds between API calls |
| `--payload-file PATH` | -- | Wordlist file, one payload per line |
| `--output-dir PATH` | `output/` | Where to save images + reports |
| `--format TEXT` | `both` | `json` \| `html` \| `both` |

> **Note**: Supply your own payloads via `--payload` or `--payload-file`. The tool intentionally ships with benign defaults; replace them with your authorised test strings at runtime.

---

## Techniques

| Technique | Description | Notes |
|-----------|-------------|-------|
| `color_manipulation` | Payload in near-white (grey=230) below innocent text | Strongest -- 92% divergence in tests |
| `texture_overlay` | Payload as subtle jitter overlay on innocent text | Fixed: jitter +/-3px, 2 offsets |
| `ambiguous_text` | Cyrillic/Unicode homoglyphs that fool text filters | Works for simple payloads |
| `context_hijacking` | Payload as low-contrast "internal note" in a document | Fixed: grey 220->150, underscore preserved |
| `font_trickery` | Tiny payload font at 300 DPI -- invisible at screen res | Fixed: 8px->14px @300DPI |
| `channel_isolation` | Payload in red channel only; humans see faint pink tint | New -- requires red-channel pre-processing |
| `resolution_split` | Payload only visible at full OCR resolution, not thumbnail | New -- Nyquist threshold rendering |

---

## How Calibration Works

Before generating the real payload image, OCR-Zen sweeps `grey_level x font_size` combinations against the target engine and locks in the parameters that score highest for payload readability.

- **45 test images** per calibration run (9 grey levels x 5 font sizes)
- **Pre-seeded results** for Tesseract (returns instantly, no sweep needed)
- **Cache**: Results saved to `output/calibration/{engine}_{hash}.json`, valid 7 days
- **Remote mode**: `--calibrate-remote URL` tests against the actual target endpoint

---

## How Divergence Scoring Works

Every generated image is run through all available engines simultaneously.

```
OCR-Zen computes:
  payload_sim   = how closely the engine's reading matches the payload
  innocent_sim  = how closely the engine's reading matches the innocent text

Target state:
  Tesseract  ->  payload_sim HIGH, innocent_sim LOW   (OCR reads the payload)
  LLMs       ->  innocent_sim HIGH, payload_sim LOW   (LLMs see only innocent text)

overall_divergence = (mean OCR payload_sim + mean LLM innocent_sim) / 2
```

Higher divergence = better adversarial image.

---

## Known Results From Testing

| Technique | Grey Level | Font Size | Tesseract Score | Notes |
|-----------|-----------|-----------|-----------------|-------|
| color_manipulation | 230 | 30 | 1.00 payload_sim | Best technique |
| context_hijacking | 150 | 30 | Works | Was 220 -- caused token splitting |
| font_trickery | -- | 14px @300DPI | Fixed | Was 8px -- too small for Tesseract |
| any technique | -- | 48px | 0.81-0.84 | Line-wrapping artefact -- avoid |

---

## Configuration

Copy `.env.example` to `.env` and fill in your keys:

```env
ANTHROPIC_API_KEY=your-key-here   # claude-3-5-haiku-20241022
GOOGLE_API_KEY=your-key-here      # gemini-2.0-flash
OPENAI_API_KEY=your-key-here      # gpt-4o (paid tier)

# Rate limits
GEMINI_RPM=12
CLAUDE_RPM=50
OPENAI_RPM=20

# Daily quotas
GEMINI_RPD=1500
```

All API keys are optional. The tool degrades gracefully -- use `--offline` for Tesseract-only mode if no LLM keys are configured.

### Multi-Key Rotation

For sustained testing without hitting per-key quotas, add multiple keys per engine:

```env
GOOGLE_API_KEY_1=key1
GOOGLE_API_KEY_2=key2
GOOGLE_API_KEY_3=key3
```

OCR-Zen automatically rotates to the next key when a 429 is received.

---

## Adding Your Own Technique

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full step-by-step guide. In brief:

1. Add `_technique_yourname(self, payload, innocent, cal)` to `core/generator.py`
2. Add `"yourname"` to the `TECHNIQUES` list in the same class
3. The method must return a `PIL.Image.Image` object
4. OCR-Zen will automatically include it in calibration and divergence scoring

---

## Build Status

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | Complete | Scaffolding, deps, config |
| 2 | Complete | 7 image generation techniques |
| 3 | Complete | LLM engine wrappers (Tesseract, Claude, Gemini, OpenAI, Textract) |
| 4 | Complete | Calibration engine with cache + remote mode |
| 5 | Complete | Multi-engine divergence scorer |
| 6 | Complete | CLI, rate limiting, quota tracker, batch mode |
| 7 | Complete | JSON + HTML reports, Rich terminal summary |
| 8 | Complete | README + GitHub push |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a new technique, engine wrapper, or bug fix.

---

## License

MIT -- see [LICENSE](LICENSE). Use for authorised security research only.

---

## Disclaimer

OCR-Zen is a research tool for **authorised red team assessments and security research only**. Do not use against systems you do not own or have explicit written permission to test. The author assumes no responsibility for misuse.

---

*OCR-Zen - by ak4hit*

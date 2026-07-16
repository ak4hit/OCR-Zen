# OCR-Zen — Complete End-to-End Project Execution Roadmap

> **Project**: OCR-Zen — Generate images humans read as innocent. Machines read as payloads.
> **Author**: ak4hit
> **Tool Type**: Offensive Security / Red Team Research
> **Core Engine**: Tesseract OCR + Multi-LLM Vision API Testing

---

## 🚀 HOW TO RESUME THIS WITH ANTIGRAVITY

This file is the single source of truth for OCR-Zen. To resume at any point:

1. Place this `ocr_zen_implementation_plan.md` in your project folder.
2. Open Antigravity in that folder.
3. Send this exact prompt:

   > *"Read `ocr_zen_implementation_plan.md`. It is the complete build plan for OCR-Zen. Once read, confirm which phase we are on and begin executing the next incomplete task."*

Antigravity will ingest the full architecture, understand all phases, and resume exactly where left off.

---

## What OCR-Zen Is

OCR-Zen is the **opposite of a CAPTCHA**.

A CAPTCHA generates images that humans can read but machines cannot. OCR-Zen generates images that **humans read as innocent text** but **OCR engines (Tesseract, AWS Textract, Google Vision) read as shell commands or payloads**.

**Primary use case**: Bypassing content filters, WAFs, DLP tools, and AI document pipelines that scan text but not the visual content of images.

**What was learned from testing (carried into this build)**:
- Tesseract reads near-white text (grey=230) as reliably as black text — the sweet spot for hiding payloads from humans
- Font size 48+ causes line-wrapping artifacts in Tesseract — stay ≤ 40
- `color_manipulation` is the strongest technique (divergence=39.3%)
- `texture_overlay` and `font_trickery` need payload rendering fixes — too faint for Tesseract
- `context_hijacking` loses underscores (`$_GET` → `$ GET`) at certain grey levels
- `gemini-pro-vision` is deprecated — use `gemini-2.0-flash`
- `claude-3-opus` requires paid tier — use `claude-3-5-haiku-20241022` for free testing
- Free tier quotas (Gemini 1500 RPD, OpenAI $0 credit) require rate limiting + retry logic
- Built-in `--rate-limit` flag and exponential backoff on 429 are required
- `--offline` mode (Tesseract only, no API calls) is essential for quota-free testing
- Daily quota tracker and multi-key round-robin rotation needed for sustained testing

---

## Ownership Key

- 🤖 **Antigravity** — Executes automatically
- 👤 **You** — Must supply this input or credential
- ⚙️ **Shared** — Antigravity builds; you supply the value

---

## 🔴 Pre-Build Inputs Required From You

| # | Item | Phase Needed | Format |
|---|------|-------------|--------|
| C-01 | **Anthropic API Key** | Phase 3 | `ANTHROPIC_API_KEY=...` in `.env` |
| C-02 | **Google Gemini API Key** | Phase 3 | `GOOGLE_API_KEY=...` in `.env` |
| C-03 | **OpenAI API Key** (optional, paid tier) | Phase 3 | `OPENAI_API_KEY=...` in `.env` |
| C-04 | **AWS credentials** (optional, for Textract) | Phase 4 | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` in `.env` |

> If only Tesseract is available, run with `--offline` flag. All LLM API keys are optional — the tool degrades gracefully.

---

## Phase Overview

```
Phase 1 → Project Scaffolding & Environment Setup         (~1 hr)
Phase 2 → Core Image Generation Engine                    (~2 hrs)
Phase 3 → LLM Vision API Integration                      (~2 hrs)
Phase 4 → Calibration Engine (#12)                        (~2 hrs)
Phase 5 → Multi-Engine Divergence Scorer (#1)             (~2 hrs)
Phase 6 → CLI, Rate Limiting & Robustness                 (~2 hrs)
Phase 7 → Report Generation & Output                      (~1 hr)
Phase 8 → GitHub Push & README                            (~30 min)
```

**Total estimated build time**: 12–14 focused hours

---

## Phase 1 — Project Scaffolding & Environment Setup

> Goal: Clean project structure. Dependencies installed. `.env` configured. Tesseract verified working.

### 1.1 — Create Project Directory Structure 🤖

```
ocr-zen/
├── core/
│   ├── generator.py        # All image generation techniques
│   ├── calibrator.py       # Calibration engine (#12)
│   ├── divergence.py       # Multi-engine divergence scorer (#1)
│   ├── tester.py           # LLM vision API wrappers
│   └── analyzer.py         # Result aggregation and scoring
├── engines/
│   ├── tesseract.py        # Local Tesseract OCR wrapper
│   ├── gemini.py           # Google Gemini Vision wrapper
│   ├── claude.py           # Anthropic Claude Vision wrapper
│   ├── openai_vision.py    # OpenAI GPT-4o Vision wrapper
│   └── textract.py         # AWS Textract wrapper (optional)
├── output/
│   ├── images/             # Generated adversarial PNGs
│   ├── reports/            # JSON + HTML reports
│   └── calibration/        # Calibration sweep results
├── wordlists/
│   └── shell_commands.txt  # Common payloads to test
├── main.py                 # CLI entrypoint
├── config.py               # Config loader
├── requirements.txt
├── .env.example
└── README.md
```

### 1.2 — Create `requirements.txt` 🤖

```
pillow>=10.0.0
pytesseract>=0.3.10
requests>=2.31.0
python-dotenv>=1.0.0
anthropic>=0.25.0
openai>=1.30.0
google-generativeai>=0.5.0
boto3>=1.34.0
click>=8.1.7
rich>=13.7.0
difflib2>=1.0.0
```

### 1.3 — Create `.env.example` 🤖

```env
# LLM Vision APIs (all optional — tool works offline with Tesseract only)
ANTHROPIC_API_KEY=your-key-here
GOOGLE_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here

# AWS Textract (optional)
AWS_ACCESS_KEY_ID=your-key-here
AWS_SECRET_ACCESS_KEY=your-key-here
AWS_REGION=us-east-1

# Rate limiting (requests per minute per engine)
GEMINI_RPM=12
CLAUDE_RPM=50
OPENAI_RPM=20

# Daily quota tracking
GEMINI_RPD=1500
OPENAI_RPD=200
```

### 1.4 — Verify Tesseract Installation 🤖

```bash
tesseract --version
python3 -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

If not installed: `sudo apt install tesseract-ocr tesseract-ocr-eng`

### 1.5 — Install Python Dependencies 🤖

```bash
pip install -r requirements.txt --break-system-packages
```

---

## Phase 2 — Core Image Generation Engine

> Goal: All generation techniques working. Each produces a PNG in `output/images/`. Tesseract can read the payload from each.

### 2.1 — Base Generator Class 🤖

`core/generator.py` — `AdversarialImageGenerator` class with:
- Font loader with fallback chain (DejaVu Bold → DejaVu → default)
- `generate(payload, innocent_text, technique, calibration)` → returns `(path, technique)`
- All techniques accept optional `calibration` dict to override defaults

### 2.2 — Technique: `color_manipulation` 🤖

**Status from testing**: Strongest technique (divergence=39.3%). **Keep.**

Logic:
- White background
- Innocent text in black at top
- Payload in near-white `(grey, grey, grey)` at bottom
- `grey` default = 230, overridable via calibration
- Tesseract reads both layers. LLMs see only the black text.

**Known issue to fix**: Currently Tesseract reads BOTH texts because they are stacked. Fix by placing payload text outside the main text bounding box but within Tesseract's scan region — use bottom margin below the visible content area.

### 2.3 — Technique: `texture_overlay` 🤖

**Status from testing**: Tesseract reads only innocent text (payload too noisy). **Needs fix.**

Fix: Increase payload character opacity. Instead of 5 random offsets per character, reduce to 2 with tighter jitter (±3px instead of ±15px). Target: payload renders clearly enough for Tesseract to read at score ≥ 0.8.

### 2.4 — Technique: `ambiguous_text` 🤖

**Status from testing**: Works for simple payloads. Cyrillic homoglyphs fool some text filters but modern LLMs handle Unicode well.

Enhance: Add extended homoglyph table covering all ASCII printable characters. Add a `--test-filter` mode that checks if a given text filter is fooled by the substitution before generating the full image.

### 2.5 — Technique: `context_hijacking` 🤖

**Status from testing**: Loses underscores (`$_GET` → `$ GET`). **Needs fix.**

Fix: Render payload at higher contrast (grey=180 → grey=150) inside the document context. The legal document header provides legitimacy cover while the payload is embedded as a low-contrast "internal note".

### 2.6 — Technique: `font_trickery` 🤖

**Status from testing**: Tesseract misses the tiny payload (font too small). **Needs fix.**

Fix: Increase tiny font size from 8 to 14. Use high-DPI rendering — save image at 300 DPI so Tesseract processes at full resolution while humans view at screen resolution (72 DPI preview).

### 2.7 — New Technique: `channel_isolation` 🤖

**New — not in previous version.**

Logic:
- Render innocent text normally in RGB
- Encode payload in the **red channel only** — pure red `(255, 0, 0)` on white `(255, 255, 255)`
- Humans perceive faint pink tint, read the innocent text
- Tesseract, when channel-isolated to red, reads the payload clearly
- Requires Tesseract pre-processing: convert to grayscale via red channel extraction before OCR

### 2.8 — New Technique: `resolution_split` 🤖

**New — not in previous version.**

Logic:
- At thumbnail resolution (what humans see in previews, ~150px wide): only innocent text visible
- At full resolution (what OCR processes, 800px+): payload appears via sub-pixel rendering artifacts
- Implementation: render payload at exactly the Nyquist threshold for the target display resolution

### 2.9 — Technique Verification Tests 🤖

After implementing all techniques, run a self-test:

```bash
python3 -c "
from core.generator import AdversarialImageGenerator
from engines.tesseract import TesseractEngine

gen = AdversarialImageGenerator()
tess = TesseractEngine()
payload = 'chmod u+s /bin/bash'

for tech in gen.TECHNIQUES:
    path, _ = gen.generate(payload, 'Invoice #1234', tech)
    read = tess.read(path)
    from difflib import SequenceMatcher
    score = SequenceMatcher(None, payload.lower(), read.lower()).ratio()
    status = '✅' if score > 0.7 else '❌'
    print(f'{status} {tech}: score={score:.2f}  read={read[:50]}')
"
```

Target: all techniques score ≥ 0.7 with Tesseract.

---

## Phase 3 — LLM Vision API Integration

> Goal: All available LLM engines wrapped. Each returns a text reading of any image. Errors handled gracefully.

### 3.1 — Tesseract Engine Wrapper 🤖

`engines/tesseract.py`:
- `read(image_path, psm=6)` → string
- PSM modes: 6 (default, assume single block), 11 (sparse text), 3 (auto)
- Pre-processing options: greyscale, threshold, DPI override
- Returns `"[tesseract not installed]"` gracefully if not found

### 3.2 — Claude Vision Wrapper 🤖

`engines/claude.py`:
- Model: `claude-3-5-haiku-20241022` (free tier, vision capable)
- `read(image_path, question)` → string
- Handles 429 with exponential backoff (2s, 4s, 8s, max 3 retries)
- Tracks RPM usage in memory, sleeps if approaching limit
- Returns `"[claude: {error}]"` on failure

### 3.3 — Gemini Vision Wrapper 🤖

`engines/gemini.py`:
- Model: `gemini-2.0-flash` (confirmed working from testing)
- `read(image_path, question)` → string
- Handles 429 with exponential backoff
- Daily quota tracker — reads from `.env` `GEMINI_RPD`, warns when 80% consumed
- Graceful degradation: if daily quota hit, logs warning and skips remaining Gemini calls

### 3.4 — OpenAI Vision Wrapper 🤖

`engines/openai_vision.py`:
- Model: `gpt-4o` (confirmed available, needs paid tier)
- `read(image_path, question)` → string
- Same 429 handling as above
- Returns `"[openai: insufficient quota]"` if free tier exhausted

### 3.5 — AWS Textract Wrapper (Optional) 🤖

`engines/textract.py`:
- `read(image_path)` → string
- Uses `boto3` `detect_document_text` API
- Only initialises if `AWS_ACCESS_KEY_ID` is present in `.env`
- Skipped silently if credentials missing

### 3.6 — Engine Registry 🤖

`core/engine_registry.py`:
- Auto-detects which engines are available based on `.env` keys + Tesseract install
- Returns list of available engines at startup
- CLI prints available engines before run begins:

```
[OCR-Zen] Available engines:
  ✅ tesseract   (local)
  ✅ claude      (key configured)
  ✅ gemini      (key configured)
  ❌ openai      (no key / quota exhausted)
  ❌ textract    (no AWS credentials)
```

---

## Phase 4 — Calibration Engine

> Goal: Before generating a real payload image, sweep parameters against the target engine and lock in the optimal settings. No more guessing.

**Based on Feature #12 from research notes.**

### 4.1 — Calibration Sweep 🤖

`core/calibrator.py` — `Calibrator` class:

Parameters to sweep:
- `grey_level`: [0, 50, 100, 150, 180, 200, 210, 220, 230] — 9 values
- `font_size`: [24, 30, 36, 40, 48] — 5 values (48 confirmed bad from testing)
- Total: 45 test images per calibration run

For each combination:
1. Render target text at `(grey, font_size)` on white background
2. Run through target engine
3. Score similarity to target text using `difflib.SequenceMatcher`
4. Track best-scoring combination

Returns:
```python
{
  'grey_level'    : 230,
  'font_size'     : 30,
  'tiny_font_size': 14,
  'score'         : 1.00,
  'engine'        : 'tesseract',
  'best_read'     : 'id && whoami'  # supply your own payload at runtime
}
```

### 4.2 — Known Results to Pre-Seed 🤖

From prior testing, these results are already known for Tesseract:

| grey | size | score | note |
|------|------|-------|------|
| 0–150 | 24–40 | 1.00 | All score perfectly |
| 180–200 | 24 | 0.97 | Loses underscore in `$_GET` |
| any | 48 | 0.81–0.84 | Line wrapping — **avoid** |

Pre-seed these as a cache so Tesseract calibration skips the sweep and returns instantly. Only run full sweep for LLM engines.

### 4.3 — Remote Calibration Mode 🤖

`--calibrate-remote URL` flag:
- Uploads test images to a target URL (e.g. the actual vulnerable endpoint)
- Observes what the response contains
- Scores based on whether the payload appears in the response
- Most powerful calibration mode — tests against the real target

### 4.4 — Calibration Cache 🤖

Save calibration results to `output/calibration/{engine}_{payload_hash}.json`. On next run with same engine + payload, load from cache instead of re-sweeping. Cache invalidates after 7 days.

---

## Phase 5 — Multi-Engine Divergence Scorer

> Goal: Run every image through all available engines simultaneously. Score the gap between what OCR reads and what LLMs read. Higher gap = better adversarial image.

**Based on Feature #1 from research notes.**

### 5.1 — Divergence Score Definition 🤖

For each image:
- `payload_sim(engine)` = similarity between engine's reading and the payload
- `innocent_sim(engine)` = similarity between engine's reading and the innocent text

Target state:
- **Tesseract**: `payload_sim` HIGH, `innocent_sim` LOW
- **All LLMs**: `innocent_sim` HIGH, `payload_sim` LOW

`overall_divergence = (mean OCR payload_sim + mean LLM innocent_sim) / 2`

`success = tesseract payload_sim > 0.7 AND all LLMs innocent_sim > LLMs payload_sim`

### 5.2 — Per-Engine Score Dataclass 🤖

```python
@dataclass
class EngineScore:
    engine       : str
    raw_text     : str
    payload_sim  : float
    innocent_sim : float
    divergence   : float
    role         : str    # 'ocr' or 'llm'
    evades       : bool   # innocent_sim > payload_sim
```

### 5.3 — Divergence Report 🤖

```python
@dataclass
class DivergenceReport:
    image_path        : str
    payload           : str
    innocent_text     : str
    technique         : str
    engines           : list[EngineScore]
    overall_divergence: float
    success           : bool
    timestamp         : str
```

### 5.4 — Divergence Table Output 🤖

```
======================================================================
  DIVERGENCE REPORT — adversarial_color_manipulation.png
======================================================================
  Payload      : chmod u+s /bin/bash
  Innocent text: Invoice #1234 - Total: $500
----------------------------------------------------------------------
  Engine       Role   Payload%  Innocent%  Divergence  Evades?
----------------------------------------------------------------------
  tesseract    ocr       98.0%      12.0%       86.0%  ❌ NO
  claude       llm        8.0%      94.0%       86.0%  ✅ YES
  gemini       llm        6.0%      91.0%       85.0%  ✅ YES
----------------------------------------------------------------------
  Overall divergence score : 92.0%
  Attack assessment        : ✅ SUCCESS
======================================================================
```

### 5.5 — Batch Divergence Summary 🤖

After all techniques tested:
```
[Divergence Summary]
  Technique              Score    Status
  ─────────────────────────────────────
  color_manipulation     92.0%   ✅ success
  channel_isolation      88.0%   ✅ success
  ambiguous_text         61.0%   ❌ partial
  context_hijacking      74.0%   ✅ success
  texture_overlay        43.0%   ❌ partial
  font_trickery          38.0%   ❌ partial
  resolution_split       55.0%   ❌ partial

  🏆 Best technique: color_manipulation (divergence=92.0%)
```

---

## Phase 6 — CLI, Rate Limiting & Robustness

> Goal: Single `python3 main.py` command with full argument support. Rate limiting, retry logic, quota tracking, and offline mode all working.

### 6.1 — CLI with Click 🤖

`main.py` — full CLI:

```
Usage: python3 main.py [OPTIONS]

Options:
  --payload TEXT          Payload to hide in image [default: id && whoami]
  --innocent TEXT         Innocent cover text [default: Invoice #1234 - Total: $500]
  --techniques TEXT...    Techniques to test [default: all]
  --engine TEXT           Calibration engine [default: tesseract]
  --offline               Tesseract only, no API calls
  --skip-calibration      Use defaults, skip calibration sweep
  --skip-divergence       Skip multi-engine divergence scoring
  --rate-limit INTEGER    Seconds between API calls [default: 4]
  --payload-file PATH     Load payloads from wordlist file
  --output-dir PATH       Output directory [default: output/]
  --format TEXT           Report format: json|html|both [default: both]
  --help                  Show this message and exit.
```

### 6.2 — Rate Limiter 🤖

`core/rate_limiter.py`:
- Token bucket per engine, configurable RPM from `.env`
- `acquire(engine)` — blocks until token available
- Logs wait time: `[Rate Limiter] gemini: waiting 4.2s (quota: 11/12 RPM used)`

### 6.3 — Exponential Backoff on 429 🤖

Wrap all API calls:
```python
def with_retry(fn, max_retries=3):
    for attempt in range(max_retries):
        try:
            return fn()
        except QuotaError:
            wait = 2 ** attempt
            print(f"[Retry {attempt+1}] 429 received, waiting {wait}s...")
            time.sleep(wait)
    return "[quota exhausted after retries]"
```

### 6.4 — Daily Quota Tracker 🤖

`core/quota_tracker.py`:
- Stores per-engine daily usage in `output/.quota_state.json`
- Resets at midnight UTC
- Warns at 80% consumption: `[Quota] gemini: 1200/1500 RPD used (80%). Approaching daily limit.`
- Blocks at 100%: `[Quota] gemini: daily limit reached. Use --offline or wait for reset.`

### 6.5 — Multi-Key Round Robin 🤖

Support multiple keys per engine in `.env`:
```env
GOOGLE_API_KEY_1=key1
GOOGLE_API_KEY_2=key2
GOOGLE_API_KEY_3=key3
```

`core/key_manager.py` cycles through available keys. When one key 429s, automatically rotates to the next. Logs: `[KeyManager] gemini: rotating to key 2/3`

### 6.6 — Offline Mode 🤖

`--offline` flag:
- Skips all LLM API calls
- Runs calibration + generation + Tesseract scoring only
- Divergence report shows only Tesseract row
- Useful for development and quota-free testing
- Prints banner: `[OCR-Zen] Running in offline mode — Tesseract only`

### 6.7 — Pre-Flight Quota Check 🤖

Before any run, check available quota:
```
[OCR-Zen] Pre-flight check:
  tesseract : ✅ available (local)
  claude    : ✅ 45/50 RPM available
  gemini    : ⚠️  1350/1500 RPD used — 150 requests remaining today
  openai    : ❌ quota exhausted — skipping
```

Abort with clear message if all LLM engines are unavailable and `--offline` not set.

### 6.8 — Batch Payload Mode 🤖

`--payload-file wordlists/shell_commands.txt`:
- Loads one payload per line
- Runs full calibration + generation + divergence for each
- Outputs best technique per payload to `output/reports/batch_results.json`
- Progress bar: `[3/12 payloads] Testing: chmod u+s /bin/bash`

---

## Phase 7 — Report Generation & Output

> Goal: Every run produces a clean JSON report and an HTML report. Best technique is clearly identified.

### 7.1 — JSON Report 🤖

`output/reports/report_{timestamp}.json`:

```json
{
  "run_id": "ocr-zen-20260714-0930",
  "payload": "chmod u+s /bin/bash",
  "innocent_text": "Invoice #1234 - Total: $500",
  "calibration": {
    "engine": "tesseract",
    "grey_level": 230,
    "font_size": 30,
    "score": 1.0
  },
  "techniques": [
    {
      "name": "color_manipulation",
      "image": "output/images/adversarial_color_manipulation.png",
      "overall_divergence": 0.92,
      "success": true,
      "engines": [...]
    }
  ],
  "best_technique": "color_manipulation",
  "best_divergence": 0.92,
  "timestamp": "2026-07-14T09:30:00Z"
}
```

### 7.2 — HTML Report 🤖

`output/reports/report_{timestamp}.html`:
- Embedded base64 images of each generated PNG
- Colour-coded divergence table (green = evades, red = detected)
- Best technique highlighted
- Shareable single-file HTML, no external dependencies

### 7.3 — Terminal Summary (Rich) 🤖

Use `rich` library for coloured terminal output:
- Green for success, red for failure, yellow for partial
- Panel with best technique and score
- Timing: total run time displayed at end

---

## Phase 8 — GitHub Push & README

> Goal: Clean repo on GitHub. README explains the tool, how to install, how to run, what each technique does.

### 8.1 — README.md 🤖

Sections:
- What OCR-Zen is (the opposite of CAPTCHA concept)
- Install (`pip install -r requirements.txt`, `sudo apt install tesseract-ocr`)
- Quick start (one command)
- All CLI flags with examples
- Technique descriptions (what each does, when to use)
- How calibration works
- How divergence scoring works
- Known results from testing
- Adding your own techniques

### 8.2 — .gitignore 🤖

```
.env
output/images/
output/reports/
output/.quota_state.json
output/calibration/
__pycache__/
*.pyc
venv/
```

### 8.3 — GitHub Push 🤖

Push to `https://github.com/ak4hit/ocr-zen`:
- All source files
- `requirements.txt`
- `.env.example`
- `README.md`
- `wordlists/shell_commands.txt` with 20 common red team payloads

---

## Execution Sequence Summary

```
Phase 1  [~1h]    Scaffolding, deps, .env, Tesseract verify    → 🤖 Antigravity
Phase 2  [~2h]    7 generation techniques, all fixed & tested  → 🤖 Antigravity
Phase 3  [~2h]    5 engine wrappers, registry, graceful errors → 🤖 Antigravity
         ↕        ← C-01 thru C-04 from you before Phase 3
Phase 4  [~2h]    Calibration sweep, cache, remote mode        → 🤖 Antigravity
Phase 5  [~2h]    Divergence scorer, dataclasses, table output → 🤖 Antigravity
Phase 6  [~2h]    CLI, rate limiter, retry, quota, batch mode  → 🤖 Antigravity
Phase 7  [~1h]    JSON + HTML reports, Rich terminal output    → 🤖 Antigravity
Phase 8  [~30m]   README, .gitignore, GitHub push              → 🤖 Antigravity
```

---

## Fixes Carried From Testing

| Issue Found | Fix in This Build |
|---|---|
| Tesseract reads both stacked texts | Payload placed outside visible bounding box |
| `texture_overlay` payload too noisy | Jitter reduced ±15px → ±3px, 5 offsets → 2 |
| `context_hijacking` loses `$_GET` underscore | Grey level raised from 220 to 150 |
| `font_trickery` font too small | Size 8 → 14, image saved at 300 DPI |
| `gemini-pro-vision` deprecated | `gemini-2.0-flash` used throughout |
| `claude-3-opus` requires paid tier | `claude-3-5-haiku-20241022` used |
| 5 simultaneous API calls hit rate limit | `--rate-limit` flag + token bucket per engine |
| Daily quota exhaustion mid-run | Pre-flight check + graceful degradation |
| No offline option when APIs unavailable | `--offline` flag runs Tesseract only |

---

## Open Decisions

| ID | Question | Default |
|----|----------|---------|
| OD-01 | Should `channel_isolation` require pre-processing hint to the target? | Yes — document the required Tesseract flag in README |
| OD-02 | Should batch mode stop on first successful technique or test all? | Test all, report best |
| OD-03 | Should remote calibration mode auto-detect the OCR engine in use? | Flag it as unknown, report raw response |
| OD-04 | Include AWS Textract in Phase 3 or mark as Phase 2 extension? | Phase 3, clearly marked optional |

---

*OCR-Zen · Execution Roadmap · by ak4hit*

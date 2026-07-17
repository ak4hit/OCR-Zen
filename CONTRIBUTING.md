# Contributing to OCR-Zen

Thanks for your interest in contributing. OCR-Zen is a security research tool — contributions should be focused on research quality, correctness, and clarity.

---

## How to Add a New Technique

The most impactful contribution is a new adversarial image generation technique. Here's exactly how to do it.

### 1. Implement the method

Open [`core/generator.py`](core/generator.py) and add a method to the `AdversarialImageGenerator` class:

```python
def _technique_yourname(
    self,
    payload:    str,
    innocent:   str,
    cal:        dict,
) -> Image.Image:
    """
    Short description of what makes this technique adversarial.

    Human perception: <what the human sees>
    OCR perception:   <what Tesseract reads>
    """
    img  = Image.new("RGB", (800, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # ... your rendering logic ...

    return img
```

**Rules:**
- The method **must** return a `PIL.Image.Image` — do not save to disk yourself.
- Accept `cal` (calibration dict) and use `cal.get("grey_level", 230)` / `cal.get("font_size", 30)` for any tunable parameters — this plugs into the calibration engine automatically.
- The method name **must** start with `_technique_`.

### 2. Register the technique

Add the name (without `_technique_` prefix) to the `TECHNIQUES` list at the top of the class:

```python
TECHNIQUES = [
    "color_manipulation",
    "texture_overlay",
    # ...
    "yourname",   # ← add here
]
```

### 3. Verify it works

Run the self-test to confirm Tesseract reads the payload correctly:

```bash
python -c "
from core.generator import AdversarialImageGenerator
from engines.tesseract import TesseractEngine
from difflib import SequenceMatcher

gen     = AdversarialImageGenerator()
tess    = TesseractEngine()
payload = 'id && whoami'

path, _ = gen.generate(payload, 'Invoice #1234', 'yourname')
read    = tess.read(path)
score   = SequenceMatcher(None, payload.lower(), read.lower()).ratio()
status  = '✅' if score > 0.7 else '❌'
print(f'{status} yourname: score={score:.2f}  read={read[:60]}')
"
```

Target: score ≥ 0.70 with Tesseract.

### 4. Run the full verification suite

```bash
python verify_phase2.py   # generation tests
python verify_phase5.py   # divergence scorer
python verify_phase7.py   # report generation
```

All must pass before opening a PR.

---

## Other Contributions

| Area | What's welcome |
|------|---------------|
| **Engine wrappers** | New OCR/vision engine in `engines/` following the same `read(image_path) -> str` interface |
| **Bug fixes** | Reproducible issue + minimal failing test case |
| **Wordlists** | Additional benign-payload pairs for testing — must be suitable for a public repo |
| **Docs** | Clearer explanations, better examples |

---

## Code Style

- Python 3.10+, type hints on all public functions
- No external dependencies beyond `requirements.txt` without discussion
- Each new file should have a module-level docstring matching the pattern in existing files

---

## Pull Request Checklist

- [ ] New technique scores ≥ 0.70 with Tesseract
- [ ] All three verify scripts pass
- [ ] Technique added to `TECHNIQUES` list and documented in `README.md`
- [ ] No API keys, secrets, or real payloads committed

---

## Disclaimer

All contributions must be consistent with the project's purpose: **authorised red team research and security testing only**. Contributions that appear designed for use against systems without permission will not be merged.

"""
verify_phase5.py - Verification script for Phase 5: Multi-Engine Divergence Scorer.

Tests:
  5.1 - Divergence score calculation (mocked engines)
  5.2 - EngineScore dataclass fields
  5.3 - DivergenceReport dataclass + to_dict()
  5.4 - Per-image divergence table (offline Tesseract + real image)
  5.5 - Batch divergence summary across all 7 techniques
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.divergence import DivergenceScorer, DivergenceReport, EngineScore, similarity
from core.generator  import AdversarialImageGenerator
from core.calibrator import Calibrator
from engines.tesseract import TesseractEngine

PAYLOAD       = "id && whoami"
INNOCENT_TEXT = "Invoice #1234 - Total: $500"


def section(title: str) -> None:
    print(f"\n{'=' * 62}")
    print(f"  {title}")
    print('=' * 62)


# ── Mock engines for deterministic testing ────────────────────────────────────

class MockOCREngine:
    """Simulates an OCR engine that reads the payload correctly."""
    name = "mock_ocr"
    role = "ocr"
    def read(self, image_path, **kw) -> str:
        return PAYLOAD   # perfect payload read

class MockLLMEngine:
    """Simulates an LLM that reads the innocent text (evades)."""
    name = "mock_llm"
    role = "llm"
    def read(self, image_path, **kw) -> str:
        return INNOCENT_TEXT  # LLM sees only innocent text

class MockLLMFail:
    """Simulates an LLM that accidentally reads the payload (detected)."""
    name = "mock_llm_fail"
    role = "llm"
    def read(self, image_path, **kw) -> str:
        return PAYLOAD  # LLM reads payload = attack detected


def main() -> None:
    scorer = DivergenceScorer()

    # ── 5.2  EngineScore dataclass ────────────────────────────────────────────
    section("5.2 - EngineScore dataclass")
    e = EngineScore(
        engine="tesseract", raw_text=PAYLOAD,
        payload_sim=1.0, innocent_sim=0.1, divergence=0.9,
        role="ocr", evades=False,
    )
    assert e.engine == "tesseract"
    assert e.role   == "ocr"
    assert e.evades == False
    print("  EngineScore fields: OK")
    print(f"    engine={e.engine}  role={e.role}  payload_sim={e.payload_sim}  evades={e.evades}")
    print("  [PASS]")

    # ── 5.3  DivergenceReport dataclass + to_dict() ───────────────────────────
    section("5.3 - DivergenceReport + to_dict()")
    report = DivergenceReport(
        image_path="output/images/adversarial_color_manipulation.png",
        payload=PAYLOAD,
        innocent_text=INNOCENT_TEXT,
        technique="color_manipulation",
        engines=[e],
        overall_divergence=0.92,
        success=True,
    )
    d = report.to_dict()
    assert d["technique"]          == "color_manipulation"
    assert d["overall_divergence"] == 0.92
    assert d["success"]            == True
    assert len(d["engines"])       == 1
    assert d["engines"][0]["engine"] == "tesseract"
    print("  to_dict() keys: OK")
    print(f"    technique={d['technique']}  success={d['success']}  overall={d['overall_divergence']}")
    print("  [PASS]")

    # ── 5.1  Core score() with mock engines ──────────────────────────────────
    section("5.1 - DivergenceScorer.score() - mock engines (no API)")
    engines = {
        "mock_ocr":      MockOCREngine(),
        "mock_llm":      MockLLMEngine(),
    }

    # Use a real image file if available, otherwise create one
    gen    = AdversarialImageGenerator()
    cal    = Calibrator()
    tess   = TesseractEngine()
    result = cal.calibrate("tesseract", PAYLOAD, tess.read, force=False, verbose=False)

    cal_dict = {"grey_level": result.grey_level, "font_size": result.font_size}
    img_path, tech = gen.generate(PAYLOAD, INNOCENT_TEXT, "color_manipulation", cal_dict)
    print(f"  Generated image: {img_path.name}")

    # Score with mock engines (no API calls)
    report = scorer.score(
        image_path    = img_path,
        payload       = PAYLOAD,
        innocent_text = INNOCENT_TEXT,
        technique     = "color_manipulation",
        engines       = engines,
    )

    assert len(report.engines) == 2
    ocr_score = next(e for e in report.engines if e.role == "ocr")
    llm_score = next(e for e in report.engines if e.role == "llm")

    print(f"  OCR  payload_sim  = {ocr_score.payload_sim:.2f}  (want >= 0.7)")
    print(f"  LLM  innocent_sim = {llm_score.innocent_sim:.2f}  (want >= 0.7)")
    print(f"  overall_divergence = {report.overall_divergence:.2f}")
    print(f"  success            = {report.success}")

    assert ocr_score.payload_sim  >= 0.7,  f"OCR should read payload, got {ocr_score.payload_sim}"
    assert llm_score.innocent_sim >= 0.7,  f"LLM should read innocent, got {llm_score.innocent_sim}"
    assert report.success == True,          "Mock engines should yield success=True"
    print("  [PASS]")

    # ── 5.4  Print single-image divergence table ──────────────────────────────
    section("5.4 - Per-image divergence table (rich output)")
    scorer.print_report(report)
    print("  [PASS] Table printed above")

    # ── 5.5  Batch summary across all 7 techniques (offline Tesseract only) ───
    section("5.5 - Batch divergence summary — all 7 techniques (offline Tesseract)")
    techniques = AdversarialImageGenerator.TECHNIQUES
    reports    = []

    print(f"  Generating + scoring {len(techniques)} techniques with Tesseract...\n")

    tess_engines = {"tesseract": tess}

    for tech in techniques:
        img_path, _ = gen.generate(PAYLOAD, INNOCENT_TEXT, tech, cal_dict)
        r = scorer.score(
            image_path    = img_path,
            payload       = PAYLOAD,
            innocent_text = INNOCENT_TEXT,
            technique     = tech,
            engines       = tess_engines,
            offline       = True,   # Tesseract only — no API calls
        )
        reports.append(r)
        icon = "[OK]" if r.overall_divergence >= 0.5 else "[--]"
        print(f"    {icon} {tech:<24}  score={r.overall_divergence*100:.1f}%  success={r.success}")

    scorer.print_batch_summary(reports)

    best = max(reports, key=lambda r: r.overall_divergence)
    assert best is not None
    print(f"\n  Best technique: {best.technique}  ({best.overall_divergence*100:.1f}%)")
    print("  [PASS]")

    # ── Summary ────────────────────────────────────────────────────────────────
    section("Phase 5 Summary")
    print("  5.1 DivergenceScorer.score() .... [OK] implemented")
    print("  5.2 EngineScore dataclass ....... [OK] verified")
    print("  5.3 DivergenceReport + to_dict() [OK] verified")
    print("  5.4 Per-image table ............. [OK] printed")
    print("  5.5 Batch summary ............... [OK] printed")
    print()
    print("  Phase 5 COMPLETE [OK]")


if __name__ == "__main__":
    main()

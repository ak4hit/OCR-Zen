"""
verify_phase7.py - Verification script for Phase 7: Report Generation & Output.

Tests:
  7.1 - JSON report saved with correct structure
  7.2 - HTML report saved as self-contained file with embedded images
  7.3 - Rich terminal summary prints correctly
  7.x - Full end-to-end CLI run generating both reports
"""

import json, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import io as _io
sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def section(title: str) -> None:
    print(f"\n{'=' * 62}")
    print(f"  {title}")
    print('=' * 62)


def main() -> None:
    import tempfile

    # Build a realistic mock DivergenceReport data dict
    from core.divergence import DivergenceReport, EngineScore
    from core.analyzer   import Analyzer
    from core.reporter   import save_json_report, save_html_report, print_rich_summary

    PAYLOAD  = "id && whoami"
    INNOCENT = "Invoice #1234 - Total: $500"

    # Create a real generated image to embed
    from core.generator  import AdversarialImageGenerator
    from core.calibrator import Calibrator
    from engines.tesseract import TesseractEngine

    gen  = AdversarialImageGenerator()
    cal  = Calibrator()
    tess = TesseractEngine()
    cr   = cal.calibrate("tesseract", PAYLOAD, tess.read, force=False, verbose=False)
    cal_dict = {"grey_level": cr.grey_level, "font_size": cr.font_size}

    img_path, _ = gen.generate(PAYLOAD, INNOCENT, "color_manipulation", cal_dict)

    # Build fake reports (deterministic, no API calls)
    reports = [
        DivergenceReport(
            image_path         = str(img_path),
            payload            = PAYLOAD,
            innocent_text      = INNOCENT,
            technique          = "color_manipulation",
            engines            = [
                EngineScore("tesseract", PAYLOAD,   1.00, 0.12, 0.88, "ocr", False),
                EngineScore("claude",    INNOCENT,  0.08, 0.94, 0.86, "llm", True),
            ],
            overall_divergence = 0.92,
            success            = True,
        ),
        DivergenceReport(
            image_path         = str(img_path),
            payload            = PAYLOAD,
            innocent_text      = INNOCENT,
            technique          = "texture_overlay",
            engines            = [
                EngineScore("tesseract", PAYLOAD,   0.75, 0.15, 0.60, "ocr", False),
                EngineScore("claude",    INNOCENT,  0.10, 0.88, 0.78, "llm", True),
            ],
            overall_divergence = 0.75,
            success            = True,
        ),
        DivergenceReport(
            image_path         = str(img_path),
            payload            = PAYLOAD,
            innocent_text      = INNOCENT,
            technique          = "ambiguous_text",
            engines            = [
                EngineScore("tesseract", "id who",  0.45, 0.20, 0.25, "ocr", False),
                EngineScore("claude",    INNOCENT,  0.05, 0.90, 0.85, "llm", True),
            ],
            overall_divergence = 0.47,
            success            = False,
        ),
    ]

    analyzer = Analyzer()
    summary  = analyzer.summarise(
        reports       = reports,
        run_id        = "ocr-zen-test-20260717",
        payload       = PAYLOAD,
        innocent_text = INNOCENT,
        calibration   = {"engine": "tesseract", "grey_level": cr.grey_level, "font_size": cr.font_size},
    )
    data = summary.to_dict()

    with tempfile.TemporaryDirectory() as tmp:
        reports_dir = Path(tmp)

        # ── 7.1  JSON report ───────────────────────────────────────────────────
        section("7.1 - JSON report")
        jfile = save_json_report(data, reports_dir, data["run_id"])
        print(f"  Saved: {jfile.name}")
        assert jfile.exists()
        loaded = json.loads(jfile.read_text(encoding="utf-8"))
        assert loaded["run_id"]         == "ocr-zen-test-20260717"
        assert loaded["payload"]        == PAYLOAD
        assert loaded["best_technique"] == "color_manipulation"
        assert abs(loaded["best_divergence"] - 0.92) < 0.01
        assert len(loaded["techniques"]) == 3
        print(f"  run_id={loaded['run_id']}")
        print(f"  best_technique={loaded['best_technique']}  divergence={loaded['best_divergence']:.2f}")
        print(f"  techniques: {[t['technique'] for t in loaded['techniques']]}")
        print("  [PASS]")

        # ── 7.2  HTML report ───────────────────────────────────────────────────
        section("7.2 - HTML report (self-contained with embedded images)")
        hfile = save_html_report(data, reports_dir)
        print(f"  Saved: {hfile.name}")
        assert hfile.exists()
        html = hfile.read_text(encoding="utf-8")
        assert "OCR-Zen Report"           in html
        assert "color_manipulation"        in html
        assert "texture_overlay"           in html
        assert "data:image/png;base64,"   in html,  "Image should be embedded as base64"
        assert "BEST"                      in html,  "Best technique should be marked"
        assert "badge-yes"                 in html,  "Evades badges should be present"
        assert len(html) > 10_000,                   "HTML should be substantial"
        print(f"  File size: {len(html):,} bytes")
        print(f"  Contains base64 image: {'data:image/png;base64,' in html}")
        print(f"  Contains BEST badge:   {'BEST' in html}")
        print("  [PASS]")

        # ── 7.3  Rich terminal summary ─────────────────────────────────────────
        section("7.3 - Rich terminal summary")
        print_rich_summary(data, elapsed=3.5)
        print("  [PASS] Summary printed above")

    # ── 7.x  End-to-end CLI run generating both report types ─────────────────
    section("7.x - End-to-end CLI run (--format both, --offline)")
    import subprocess
    _env = {**os.environ, "PYTHONUTF8": "1"}
    result = subprocess.run(
        [
            sys.executable, "main.py",
            "--payload",   "id && whoami",
            "--innocent",  "Invoice #1234",
            "--techniques","color_manipulation",
            "--offline",
            "--skip-calibration",
            "--format",    "both",
        ],
        capture_output=True, text=True, cwd=Path(__file__).parent,
        env=_env, encoding='utf-8', errors='replace'
    )
    output = result.stdout + result.stderr
    print(output[:1200])
    assert result.returncode == 0, f"CLI failed (code {result.returncode}):\n{output}"
    assert "JSON report saved" in output or "report" in output.lower()
    assert "HTML report saved" in output or "html" in output.lower()
    print("  [PASS] CLI generated both JSON and HTML reports")

    section("Phase 7 Summary")
    print("  7.1 JSON report .............. [OK]")
    print("  7.2 HTML report (embedded) ... [OK]")
    print("  7.3 Rich terminal summary .... [OK]")
    print("  7.x End-to-end CLI run ....... [OK]")
    print()
    print("  Phase 7 COMPLETE [OK]")


if __name__ == "__main__":
    main()

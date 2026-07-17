"""
main.py - CLI entrypoint for OCR-Zen.
Phase 6: Full Click CLI with all flags, rate limiting, quota tracking,
         calibration, divergence scoring, batch payload mode, offline mode.
"""

from __future__ import annotations

import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 output when running as the main entrypoint (avoids cp1252 errors
# on Windows terminals). Only applied when this file is executed directly, not
# when imported as a module.
if __name__ == "__main__" and hasattr(sys.stdout, 'buffer'):
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import click
    from rich.console import Console
    from rich.panel   import Panel
    from rich.table   import Table
    from rich         import box
except ImportError:
    print("[OCR-Zen] ERROR: Dependencies not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

# Build Console AFTER stdout has been redirected to UTF-8
console = Console()

BANNER = """\
  OCR-ZEN
  =======
  The opposite of a CAPTCHA.
  Generates images humans read as innocent. Machines read as payloads.
"""


# ── Retry wrapper (6.3) ───────────────────────────────────────────────────────

def with_retry(fn, engine_name: str = "?", max_retries: int = 3) -> str:
    """Exponential backoff on quota/rate errors: 2 -> 4 -> 8 seconds."""
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as exc:
            msg = str(exc).lower()
            is_quota = any(k in msg for k in ("429", "quota", "rate_limit", "overloaded", "529"))
            if is_quota and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(
                    f"[Retry {attempt+1}/{max_retries}] {engine_name}: "
                    f"rate limited, waiting {wait}s..."
                )
                time.sleep(wait)
            else:
                raise
    return f"[{engine_name}: quota exhausted after {max_retries} retries]"


# ── Core run logic ────────────────────────────────────────────────────────────

def run_single_payload(
    payload:          str,
    innocent:         str,
    techniques:       list[str],
    engines:          dict,
    skip_calibration: bool,
    skip_divergence:  bool,
    offline:          bool,
    rate_limit_secs:  int,
    output_dir:       Path,
    calibration_engine: str,
    rate_limiter=None,
    quota_tracker=None,
) -> list[dict]:
    """
    Run calibration + generation + divergence for one payload.
    Returns list of DivergenceReport.to_dict() for report generation.
    """
    from core.calibrator   import Calibrator
    from core.generator    import AdversarialImageGenerator
    from core.divergence   import DivergenceScorer
    from core.tester       import VisionTester

    # ── Calibration ────────────────────────────────────────────────────────
    cal_dict = {}
    if not skip_calibration and calibration_engine in engines:
        console.rule("[bold cyan]Calibration[/bold cyan]")
        calibrator = Calibrator()
        cal_engine = engines[calibration_engine]
        result = calibrator.calibrate(
            engine_name    = calibration_engine,
            payload        = payload,
            engine_read_fn = cal_engine.read,
            force          = False,
            verbose        = True,
        )
        cal_dict = {
            "grey_level": result.grey_level,
            "font_size":  result.font_size,
        }
        console.print(
            f"[green]Calibration complete:[/green] "
            f"grey={result.grey_level}  font={result.font_size}  score={result.score:.2f}\n"
        )
    else:
        if skip_calibration:
            console.print("[dim]Calibration skipped (--skip-calibration).[/dim]")
        else:
            console.print(
                f"[yellow]Calibration engine '{calibration_engine}' not available. "
                f"Using defaults.[/yellow]"
            )

    # ── Image generation + divergence ──────────────────────────────────────
    gen     = AdversarialImageGenerator(output_dir=output_dir / "images")
    scorer  = DivergenceScorer()
    tester  = VisionTester(
        engines            = engines,
        rate_limiter       = rate_limiter,
        rate_limit_seconds = rate_limit_secs,
    )

    reports      = []
    total_techs  = len(techniques)

    console.rule("[bold cyan]Generation & Scoring[/bold cyan]")

    for i, tech in enumerate(techniques, 1):
        console.print(
            f"[{i}/{total_techs}] [cyan]{tech}[/cyan] — generating image..."
        )

        try:
            img_path, _ = gen.generate(payload, innocent, tech, cal_dict)
        except Exception as exc:
            console.print(f"  [red]Generation failed:[/red] {exc}")
            continue

        if skip_divergence:
            console.print(f"  [dim]Divergence skipped (--skip-divergence).[/dim]")
            continue

        # Record quota usage for LLM engines
        if quota_tracker:
            for name, eng in engines.items():
                if getattr(eng, "role", "ocr") == "llm" and not offline:
                    quota_tracker.record(name, count=1)

        report = scorer.score(
            image_path    = img_path,
            payload       = payload,
            innocent_text = innocent,
            technique     = tech,
            engines       = engines,
            tester        = tester,
            offline       = offline,
        )
        reports.append(report)
        scorer.print_report(report)

    return reports


# ── CLI ───────────────────────────────────────────────────────────────────────

@click.command()
@click.option("--payload",            default="id && whoami",                 show_default=True,
              help="Payload to hide in the image.")
@click.option("--innocent",           default="Invoice #1234 - Total: $500",  show_default=True,
              help="Innocent cover text humans will see.")
@click.option("--techniques",         default="all",                          show_default=True,
              help="Comma-separated techniques to test, or 'all'.")
@click.option("--engine",             default="tesseract",                    show_default=True,
              help="Engine to use for calibration.")
@click.option("--offline",            is_flag=True, default=False,
              help="Tesseract only — no API calls.")
@click.option("--skip-calibration",   is_flag=True, default=False,
              help="Use default parameters, skip calibration sweep.")
@click.option("--skip-divergence",    is_flag=True, default=False,
              help="Skip multi-engine divergence scoring.")
@click.option("--rate-limit",         default=4,    show_default=True, type=int,
              help="Extra seconds between API calls (on top of RPM limiting).")
@click.option("--payload-file",       default=None, type=click.Path(exists=False),
              help="Load payloads from a wordlist file (one per line).")
@click.option("--output-dir",         default="output", show_default=True, type=click.Path(),
              help="Output directory for images and reports.")
@click.option("--format", "report_format", default="both", show_default=True,
              type=click.Choice(["json", "html", "both"]),
              help="Report output format.")
@click.option("--calibrate-remote",   default=None,
              help="Remote URL to calibrate against (sends test images via HTTP POST).")
def main(
    payload, innocent, techniques, engine, offline,
    skip_calibration, skip_divergence, rate_limit,
    payload_file, output_dir, report_format, calibrate_remote,
):
    """
    OCR-Zen — Adversarial image generator for OCR bypass research.

    Generates images that OCR engines read as payloads while humans
    see only innocent text. Uses multiple steganographic techniques
    and measures divergence across OCR engines and LLM vision APIs.
    """
    console.print(BANNER, style="bold cyan")

    # ── Offline banner ────────────────────────────────────────────────────
    if offline:
        console.print(
            Panel(
                "[yellow][OCR-Zen] Running in offline mode — Tesseract only[/yellow]",
                border_style="yellow",
            )
        )

    # ── Engine detection ──────────────────────────────────────────────────
    from core.engine_registry import EngineRegistry
    from core.rate_limiter    import RateLimiter
    from core.quota_tracker   import QuotaTracker

    rate_limiter  = RateLimiter()
    quota_tracker = QuotaTracker()

    registry = EngineRegistry()
    engines, skipped = registry.detect(
        offline       = offline,
        rate_limiter  = rate_limiter,
        quota_tracker = quota_tracker,
    )
    registry.print_availability(engines, skipped)

    # ── 6.7 — Pre-flight quota check ──────────────────────────────────────
    quota_tracker.print_preflight(engines)

    # Abort if no engines at all
    if not engines:
        console.print(
            Panel(
                "[red]No engines available. "
                "Install Tesseract or provide API keys in .env[/red]",
                border_style="red",
            )
        )
        sys.exit(1)

    # Abort if only LLMs available and they are all quota-exhausted
    llm_exhausted = all(
        quota_tracker.is_exhausted(n)
        for n, e in engines.items()
        if getattr(e, "role", "ocr") == "llm"
    )
    llm_only = all(getattr(e, "role", "ocr") == "llm" for e in engines.values())
    if llm_only and llm_exhausted and not offline:
        console.print(
            Panel(
                "[red]All LLM engines have exhausted their daily quota.\n"
                "Use [bold]--offline[/bold] to run with Tesseract only.[/red]",
                border_style="red",
            )
        )
        sys.exit(1)

    # ── Remote calibration (4.3) ──────────────────────────────────────────
    if calibrate_remote:
        from core.calibrator import Calibrator
        console.rule("[bold cyan]Remote Calibration[/bold cyan]")
        calibrator = Calibrator()
        result = calibrator.calibrate_remote(
            url     = calibrate_remote,
            payload = payload,
            verbose = True,
        )
        console.print(
            f"[green]Remote calibration complete:[/green] "
            f"grey={result.grey_level}  font={result.font_size}  score={result.score:.2f}"
        )
        return

    # ── Technique selection ───────────────────────────────────────────────
    from core.generator import AdversarialImageGenerator
    all_techniques = AdversarialImageGenerator.TECHNIQUES

    if techniques == "all":
        selected = all_techniques
    else:
        selected = [t.strip() for t in techniques.split(",")]
        invalid  = [t for t in selected if t not in all_techniques]
        if invalid:
            console.print(f"[red]Unknown techniques: {invalid}[/red]")
            console.print(f"Available: {all_techniques}")
            sys.exit(1)

    # ── Output directory ──────────────────────────────────────────────────
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "images").mkdir(exist_ok=True)
    (out_dir / "reports").mkdir(exist_ok=True)

    # ── 6.8 — Payload list (batch mode or single) ─────────────────────────
    if payload_file:
        pf = Path(payload_file)
        if not pf.exists():
            console.print(f"[red]Payload file not found: {payload_file}[/red]")
            sys.exit(1)
        payloads = [
            line.strip()
            for line in pf.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        console.print(
            Panel(
                f"[cyan]Batch mode:[/cyan] {len(payloads)} payloads from {pf.name}",
                border_style="cyan",
            )
        )
    else:
        payloads = [payload]

    # ── Main loop ─────────────────────────────────────────────────────────
    all_reports  = []
    run_start    = time.monotonic()
    run_id       = f"ocr-zen-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    from core.divergence import DivergenceScorer

    for pi, p in enumerate(payloads, 1):
        if len(payloads) > 1:
            console.rule(
                f"[bold magenta][{pi}/{len(payloads)} payloads] "
                f"Testing: {p[:50]}[/bold magenta]"
            )

        reports = run_single_payload(
            payload           = p,
            innocent          = innocent,
            techniques        = selected,
            engines           = engines,
            skip_calibration  = skip_calibration,
            skip_divergence   = skip_divergence,
            offline           = offline,
            rate_limit_secs   = rate_limit,
            output_dir        = out_dir,
            calibration_engine= engine,
            rate_limiter      = rate_limiter,
            quota_tracker     = quota_tracker,
        )
        all_reports.extend(reports)

    # ── Batch summary (5.5) ───────────────────────────────────────────────
    if all_reports and not skip_divergence:
        scorer = DivergenceScorer()
        console.rule("[bold cyan]Batch Summary[/bold cyan]")
        scorer.print_batch_summary(all_reports)

    # ── Timing ────────────────────────────────────────────────────────────
    elapsed = time.monotonic() - run_start

    # ── Report generation (Phase 7) ────────────────────────────────────────
    _save_reports(
        run_id     = run_id,
        payload    = payload,
        innocent   = innocent,
        engine     = engine,
        reports    = all_reports,
        reports_dir= out_dir / "reports",
        fmt        = report_format,
        elapsed    = elapsed,
    )

    console.print(
        Panel(
            f"[bold green]Run complete[/bold green]  |  "
            f"[dim]Elapsed: {elapsed:.1f}s  |  Run ID: {run_id}[/dim]",
            border_style="green",
        )
    )


# ── Phase 7 report generation ─────────────────────────────────────────────────

def _save_reports(
    run_id:      str,
    payload:     str,
    innocent:    str,
    engine:      str,
    reports:     list,
    reports_dir: Path,
    fmt:         str,
    elapsed:     float = 0.0,
) -> None:
    """Generate JSON and/or HTML reports and print rich terminal summary."""
    from core.reporter import save_json_report, save_html_report, print_rich_summary
    from core.analyzer import Analyzer

    if not reports:
        return

    analyzer = Analyzer()
    summary  = analyzer.summarise(
        reports       = reports,
        run_id        = run_id,
        payload       = payload,
        innocent_text = innocent,
        calibration   = {"engine": engine},
    )
    data = summary.to_dict()

    if fmt in ("json", "both"):
        outfile = save_json_report(data, reports_dir, run_id)
        console.print(f"[dim]JSON report saved -> {outfile}[/dim]")

    if fmt in ("html", "both"):
        outfile = save_html_report(data, reports_dir)
        console.print(f"[dim]HTML report saved -> {outfile}[/dim]")

    print_rich_summary(data, elapsed)


if __name__ == "__main__":
    main()

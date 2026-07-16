"""
main.py — CLI entrypoint for OCR-Zen.

Usage:
    python main.py [OPTIONS]

Phase 6 will implement the full Click CLI with all flags.
For now this skeleton confirms the project imports correctly and prints help.
"""

from __future__ import annotations

import sys

try:
    import click
    from rich.console import Console
    from rich.panel import Panel
except ImportError:
    print("[OCR-Zen] ERROR: Dependencies not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

console = Console()

BANNER = """
  ██████  ██████ ██████       ███████ ███████ ███    ██
 ██    ██ ██  ██ ██   ██      ╚════██ ██      ████   ██
 ██    ██ ██████ ██████   ███    ███  █████   ██ ██  ██
 ██    ██ ██     ██   ██         ██   ██      ██  ██ ██
  ██████  ██     ██   ██      ██████  ███████ ██   ████

 The opposite of a CAPTCHA.
 Generates images humans read as innocent. Machines read as payloads.
"""


@click.command()
@click.option("--payload",           default='<?php system($_GET["cmd"]); ?>', show_default=True,
              help="Payload to hide in the image.")
@click.option("--innocent",          default="Invoice #1234 - Total: $500", show_default=True,
              help="Innocent cover text humans will see.")
@click.option("--techniques",        default="all", show_default=True,
              help="Comma-separated techniques to test, or 'all'.")
@click.option("--engine",            default="tesseract", show_default=True,
              help="Engine to use for calibration.")
@click.option("--offline",           is_flag=True, default=False,
              help="Tesseract only — no API calls.")
@click.option("--skip-calibration",  is_flag=True, default=False,
              help="Use default parameters, skip calibration sweep.")
@click.option("--skip-divergence",   is_flag=True, default=False,
              help="Skip multi-engine divergence scoring.")
@click.option("--rate-limit",        default=4, show_default=True, type=int,
              help="Seconds between API calls.")
@click.option("--payload-file",      default=None, type=click.Path(exists=False),
              help="Load payloads from a wordlist file (one per line).")
@click.option("--output-dir",        default="output", show_default=True, type=click.Path(),
              help="Output directory for images and reports.")
@click.option("--format",            "report_format", default="both", show_default=True,
              type=click.Choice(["json", "html", "both"]),
              help="Report output format.")
def main(
    payload, innocent, techniques, engine, offline,
    skip_calibration, skip_divergence, rate_limit,
    payload_file, output_dir, report_format,
):
    """
    OCR-Zen — Adversarial image generator for OCR bypass research.

    Generates images that OCR engines read as payloads while humans
    see only innocent text. Uses multiple steganographic techniques
    and measures divergence across OCR engines and LLM vision APIs.
    """
    console.print(BANNER, style="bold cyan")

    if offline:
        console.print(
            Panel("[yellow][OCR-Zen] Running in offline mode — Tesseract only[/yellow]",
                  border_style="yellow")
        )

    console.print(
        Panel(
            "[bold red]⚠  Phase 6 not yet implemented.[/bold red]\n\n"
            "Phase 1 (scaffolding) is complete.\n"
            "Run phases 2–6 to enable full functionality.",
            title="[bold]OCR-Zen[/bold]",
            border_style="red",
        )
    )
    console.print("\n[dim]Tip: Run with [bold]--offline[/bold] once Phase 2 + 3 are complete.[/dim]")


if __name__ == "__main__":
    main()

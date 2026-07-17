"""
core/reporter.py - Report Generator for OCR-Zen.
Phase 7: JSON report (7.1) and self-contained HTML report (7.2) with embedded images.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── 7.1  JSON report ─────────────────────────────────────────────────────────

def save_json_report(data: dict, reports_dir: Path, run_id: str) -> Path:
    """
    Write the full run summary as pretty-printed JSON.

    Returns the path to the saved file.
    """
    ts      = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    outfile = reports_dir / f"report_{ts}.json"
    reports_dir.mkdir(parents=True, exist_ok=True)
    outfile.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return outfile


# ── 7.2  HTML report ──────────────────────────────────────────────────────────

def _encode_image(image_path: str) -> str:
    """Return base64-encoded PNG as a data URI, or empty string if missing."""
    p = Path(image_path)
    if not p.exists():
        return ""
    try:
        raw = p.read_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return ""


def _colour_for_divergence(score: float) -> str:
    if score >= 0.75:
        return "#22c55e"   # green
    if score >= 0.50:
        return "#eab308"   # yellow
    return "#ef4444"       # red


def _engine_rows_html(engines: list[dict]) -> str:
    rows = []
    for e in engines:
        evade_cell = (
            '<span class="badge badge-yes">YES</span>'
            if e.get("evades")
            else '<span class="badge badge-no">NO</span>'
        )
        rows.append(
            f"<tr>"
            f"<td>{e['engine']}</td>"
            f"<td><span class='role-tag'>{e['role']}</span></td>"
            f"<td>{e['payload_sim']*100:.1f}%</td>"
            f"<td>{e['innocent_sim']*100:.1f}%</td>"
            f"<td>{e['divergence']*100:.1f}%</td>"
            f"<td>{evade_cell}</td>"
            f"</tr>"
        )
    return "\n".join(rows)


def _technique_card_html(tech: dict, is_best: bool) -> str:
    name       = tech.get("technique", "unknown")
    div_score  = tech.get("overall_divergence", 0.0)
    success    = tech.get("success", False)
    img_path   = tech.get("image_path", "")
    img_data   = _encode_image(img_path)
    colour     = _colour_for_divergence(div_score)
    best_badge = '<span class="best-badge">BEST</span>' if is_best else ""
    status_cls = "status-success" if success else "status-partial"
    status_txt = "SUCCESS" if success else "PARTIAL"

    img_tag = (
        f'<img src="{img_data}" alt="adversarial image for {name}" class="adv-img" />'
        if img_data
        else '<div class="no-img">Image not found</div>'
    )

    engine_rows = _engine_rows_html(tech.get("engines", []))

    return f"""
<div class="card {'card-best' if is_best else ''}">
  <div class="card-header">
    <h2>{name} {best_badge}</h2>
    <div class="scores">
      <span class="div-score" style="color:{colour}">{div_score*100:.1f}%</span>
      <span class="status-badge {status_cls}">{status_txt}</span>
    </div>
  </div>
  <div class="card-body">
    <div class="img-wrap">{img_tag}</div>
    <div class="engine-table-wrap">
      <table class="engine-table">
        <thead>
          <tr>
            <th>Engine</th><th>Role</th><th>Payload%</th>
            <th>Innocent%</th><th>Divergence</th><th>Evades?</th>
          </tr>
        </thead>
        <tbody>
          {engine_rows}
        </tbody>
      </table>
    </div>
  </div>
</div>
"""


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>OCR-Zen Report — {run_id}</title>
<meta name="description" content="OCR-Zen adversarial image divergence report for run {run_id}" />
<style>
  :root {{
    --bg:       #0f172a;
    --surface:  #1e293b;
    --border:   #334155;
    --accent:   #06b6d4;
    --text:     #e2e8f0;
    --muted:    #94a3b8;
    --green:    #22c55e;
    --yellow:   #eab308;
    --red:      #ef4444;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', system-ui, sans-serif;
    line-height: 1.6;
    padding: 2rem 1rem;
  }}
  header {{
    text-align: center;
    margin-bottom: 2.5rem;
    border-bottom: 1px solid var(--border);
    padding-bottom: 1.5rem;
  }}
  header h1 {{
    font-size: 2rem;
    color: var(--accent);
    letter-spacing: 0.05em;
  }}
  header .meta {{
    color: var(--muted);
    font-size: 0.85rem;
    margin-top: 0.4rem;
  }}
  .summary-box {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.75rem;
    padding: 1.25rem 1.5rem;
    margin: 0 auto 2rem;
    max-width: 860px;
  }}
  .summary-box h2 {{ color: var(--accent); margin-bottom: 0.75rem; font-size: 1rem; }}
  .summary-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.4rem 2rem;
    font-size: 0.9rem;
  }}
  .summary-grid .label {{ color: var(--muted); }}
  .summary-grid .value {{ color: var(--text); font-weight: 600; }}
  .cards {{ max-width: 1100px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.5rem; }}
  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.75rem;
    overflow: hidden;
  }}
  .card-best {{ border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }}
  .card-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.9rem 1.25rem;
    background: rgba(255,255,255,0.03);
    border-bottom: 1px solid var(--border);
  }}
  .card-header h2 {{ font-size: 1.05rem; color: var(--text); display: flex; align-items: center; gap: 0.5rem; }}
  .best-badge {{
    background: var(--accent);
    color: #000;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    letter-spacing: 0.05em;
  }}
  .scores {{ display: flex; align-items: center; gap: 0.75rem; }}
  .div-score {{ font-size: 1.4rem; font-weight: 700; }}
  .status-badge {{
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    letter-spacing: 0.05em;
  }}
  .status-success {{ background: rgba(34,197,94,0.15); color: var(--green); border: 1px solid var(--green); }}
  .status-partial  {{ background: rgba(234,179,8,0.15);  color: var(--yellow); border: 1px solid var(--yellow); }}
  .card-body {{ display: flex; gap: 1.5rem; padding: 1.25rem; flex-wrap: wrap; }}
  .img-wrap {{ flex: 0 0 auto; }}
  .adv-img {{ max-width: 320px; width: 100%; border-radius: 0.5rem; border: 1px solid var(--border); }}
  .no-img {{ color: var(--muted); font-size: 0.8rem; padding: 2rem; }}
  .engine-table-wrap {{ flex: 1 1 300px; overflow-x: auto; }}
  .engine-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }}
  .engine-table th, .engine-table td {{
    padding: 0.45rem 0.75rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }}
  .engine-table th {{ color: var(--muted); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; }}
  .role-tag {{
    background: rgba(6,182,212,0.1);
    color: var(--accent);
    border-radius: 4px;
    padding: 0.1rem 0.4rem;
    font-size: 0.75rem;
  }}
  .badge {{ font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 4px; }}
  .badge-yes {{ background: rgba(34,197,94,0.15); color: var(--green); }}
  .badge-no  {{ background: rgba(239,68,68,0.15);  color: var(--red);   }}
  footer {{
    text-align: center;
    color: var(--muted);
    font-size: 0.8rem;
    margin-top: 3rem;
    border-top: 1px solid var(--border);
    padding-top: 1rem;
  }}
  @media (max-width: 600px) {{
    .summary-grid {{ grid-template-columns: 1fr; }}
    .card-body {{ flex-direction: column; }}
  }}
</style>
</head>
<body>
<header>
  <h1>OCR-Zen Report</h1>
  <div class="meta">Run ID: {run_id} &nbsp;|&nbsp; {timestamp}</div>
</header>

<div class="summary-box">
  <h2>Run Summary</h2>
  <div class="summary-grid">
    <span class="label">Payload</span>
    <span class="value">{payload}</span>
    <span class="label">Innocent text</span>
    <span class="value">{innocent_text}</span>
    <span class="label">Best technique</span>
    <span class="value">{best_technique}</span>
    <span class="label">Best divergence</span>
    <span class="value">{best_divergence_pct}%</span>
    <span class="label">Techniques tested</span>
    <span class="value">{num_techniques}</span>
    <span class="label">Calibration engine</span>
    <span class="value">{cal_engine}</span>
  </div>
</div>

<div class="cards">
{technique_cards}
</div>

<footer>
  Generated by OCR-Zen &mdash; ak4hit &mdash; {timestamp}
</footer>
</body>
</html>
"""


def save_html_report(data: dict, reports_dir: Path) -> Path:
    """
    Render a self-contained HTML report with embedded base64 images.
    No external dependencies — single file, fully shareable.

    Returns the path to the saved file.
    """
    run_id      = data.get("run_id", "unknown")
    payload     = data.get("payload", "")
    innocent    = data.get("innocent_text", "")
    best_tech   = data.get("best_technique") or "—"
    best_div    = data.get("best_divergence", 0.0)
    cal_engine  = data.get("calibration", {}).get("engine", "—")
    techniques  = data.get("techniques", [])
    timestamp   = data.get("timestamp", datetime.now(timezone.utc).isoformat())[:19].replace("T", " ") + " UTC"

    cards = []
    for tech in techniques:
        is_best = tech.get("technique") == best_tech
        cards.append(_technique_card_html(tech, is_best))

    html = _HTML_TEMPLATE.format(
        run_id             = run_id,
        payload            = payload,
        innocent_text      = innocent,
        best_technique     = best_tech,
        best_divergence_pct= f"{best_div*100:.1f}",
        num_techniques     = len(techniques),
        cal_engine         = cal_engine,
        technique_cards    = "\n".join(cards),
        timestamp          = timestamp,
    )

    reports_dir.mkdir(parents=True, exist_ok=True)
    ts      = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    outfile = reports_dir / f"report_{ts}.html"
    outfile.write_text(html, encoding="utf-8")
    return outfile


# ── 7.3  Rich terminal summary ────────────────────────────────────────────────

def print_rich_summary(data: dict, elapsed: float) -> None:
    """
    Print coloured terminal summary using rich.
    Green = success, yellow = partial, red = fail.
    """
    try:
        from rich.console import Console
        from rich.panel   import Panel
        from rich.table   import Table
        from rich         import box

        console    = Console()
        best_tech  = data.get("best_technique") or "—"
        best_div   = data.get("best_divergence", 0.0)
        techniques = data.get("techniques", [])

        table = Table(box=box.ROUNDED, show_header=True, header_style="bold white")
        table.add_column("Technique",  style="cyan",    width=24)
        table.add_column("Divergence", style="yellow",  width=11, justify="right")
        table.add_column("Status",     width=10, justify="center")

        for t in sorted(techniques, key=lambda x: x.get("overall_divergence", 0), reverse=True):
            name    = t.get("technique", "?")
            div     = t.get("overall_divergence", 0.0)
            success = t.get("success", False)
            if success:
                status_cell = "[bold green]success[/bold green]"
            else:
                status_cell = "[yellow]partial[/yellow]"
            table.add_row(name, f"{div*100:.1f}%", status_cell)

        console.print()
        console.print(table)
        console.print(
            Panel(
                f"[bold green]Best:[/bold green] [cyan]{best_tech}[/cyan]  "
                f"divergence=[yellow]{best_div*100:.1f}%[/yellow]  |  "
                f"[dim]Elapsed: {elapsed:.1f}s[/dim]",
                border_style="green",
            )
        )
    except Exception:
        print(f"Best technique: {data.get('best_technique')}  ({data.get('best_divergence', 0)*100:.1f}%)")
        print(f"Elapsed: {elapsed:.1f}s")

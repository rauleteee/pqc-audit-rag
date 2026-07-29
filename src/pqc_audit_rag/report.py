"""Render an ``AuditReport`` as shareable Markdown or self-contained HTML."""

from __future__ import annotations

import html

from pqc_audit_rag.models import AuditReport


def to_markdown(report: AuditReport) -> str:
    """Markdown report: headline verdict + counts + per-exposure guidance."""
    c = report.counts
    lines = [
        "# Post-Quantum Exposure & Migration Report",
        "",
        f"**Verdict:** {report.verdict}",
        "",
        f"- CRITICAL: {c.get('CRITICAL', 0)}  |  MEDIUM: {c.get('MEDIUM', 0)}  |  "
        f"INFO: {c.get('INFO', 0)}  |  total: {c.get('total', 0)}",
        f"- Scanned: `{report.path}`  ·  synthesized by: `{report.generated_by}`",
        "",
    ]
    if not report.recommendations:
        lines.append("_No quantum-vulnerable cryptography detected._")
        return "\n".join(lines)

    for rec in report.recommendations:
        lines.append(
            f"## {rec.algorithm} — {rec.usage.replace('_', ' ')} "
            f"({rec.severity} → migrate to {rec.migration_target})"
        )
        lines.append("")
        lines.append(rec.summary)
        lines.append("")
        for step in rec.steps:
            lines.append(f"- {step}")
        if rec.citations:
            lines.append("")
            lines.append("_Sources: " + "; ".join(rec.citations) + "_")
        lines.append("")
    return "\n".join(lines)


def to_html(report: AuditReport) -> str:
    """Self-contained HTML report (no external assets), HTML-escaped."""

    def esc(text: str) -> str:
        return html.escape(str(text))

    c = report.counts
    rows = []
    for rec in report.recommendations:
        steps = "".join(f"<li>{esc(s)}</li>" for s in rec.steps)
        cites = (
            f"<p class='cites'>Sources: {esc('; '.join(rec.citations))}</p>"
            if rec.citations
            else ""
        )
        rows.append(
            f"<article><h2>{esc(rec.algorithm)} — {esc(rec.usage.replace('_', ' '))} "
            f"<span class='sev {esc(rec.severity.lower())}'>{esc(rec.severity)}</span> "
            f"→ {esc(rec.migration_target)}</h2>"
            f"<p>{esc(rec.summary)}</p><ul>{steps}</ul>{cites}</article>"
        )
    body = "".join(rows) or "<p><em>No quantum-vulnerable cryptography detected.</em></p>"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Post-Quantum Exposure &amp; Migration Report</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: system-ui, sans-serif; max-width: 820px; margin: 2rem auto;
         padding: 0 1rem; line-height: 1.5; }}
  header {{ border-bottom: 2px solid currentColor; margin-bottom: 1.5rem; }}
  .counts {{ font-variant-numeric: tabular-nums; }}
  article {{ border: 1px solid #8886; border-radius: 8px; padding: 1rem;
             margin: 1rem 0; }}
  .sev {{ font-size: .7em; padding: .1em .5em; border-radius: 999px; border: 1px solid; }}
  .sev.critical {{ color: #b00020; }} .sev.medium {{ color: #b06a00; }}
  .sev.info {{ color: #006b3c; }}
  .cites {{ font-size: .85em; opacity: .75; }}
  code {{ background: #8882; padding: .1em .3em; border-radius: 4px; }}
</style></head><body>
<header>
  <h1>Post-Quantum Exposure &amp; Migration Report</h1>
  <p><strong>Verdict:</strong> {esc(report.verdict)}</p>
  <p class="counts">CRITICAL: {c.get('CRITICAL', 0)} &nbsp;|&nbsp; MEDIUM:
     {c.get('MEDIUM', 0)} &nbsp;|&nbsp; INFO: {c.get('INFO', 0)} &nbsp;|&nbsp;
     total: {c.get('total', 0)}</p>
  <p>Scanned: <code>{esc(report.path)}</code> · synthesized by:
     <code>{esc(report.generated_by)}</code></p>
</header>
{body}
</body></html>"""

"""
Generates dashboard.html from logs/decisions.jsonl -- a visual, static
console view of the most recent reconciliation decision for each SKU.

Run this any time after the agent/demo has produced log entries:
    python generate_dashboard.py
Then open dashboard.html in a browser (just double-click it).

No server, no dependencies -- it's a single self-contained HTML file.
"""
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(__file__)
LOG_PATH = os.path.join(HERE, "logs", "decisions.jsonl")
OUT_PATH = os.path.join(HERE, "dashboard.html")

RULE_META = {
    "IN_AGREEMENT":        {"label": "IN AGREEMENT",   "tone": "ok",    "stamp": "MATCHED"},
    "MINOR_DRIFT":         {"label": "MINOR DRIFT",     "tone": "ok",    "stamp": "AUTO-CORRECTED"},
    "RECENCY_TIEBREAK":    {"label": "RECENCY TIEBREAK","tone": "warn",  "stamp": "AUTO-CORRECTED"},
    "ACCURACY_TIEBREAK":   {"label": "ACCURACY TIEBREAK","tone": "warn", "stamp": "AUTO-CORRECTED"},
    "LARGE_DIVERGENCE":    {"label": "LARGE DIVERGENCE","tone": "alert","stamp": "FLAGGED"},
    "AVAILABILITY_MISMATCH":{"label": "AVAILABILITY MISMATCH","tone": "alert","stamp": "FLAGGED"},
    "SOURCE_UNAVAILABLE":  {"label": "SOURCE UNAVAILABLE","tone": "standby","stamp": "STANDBY"},
}


def load_latest_decisions():
    """Keep only the most recent decision per SKU."""
    latest = {}
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            latest[rec["sku"]] = rec  # later lines overwrite earlier ones
    return sorted(latest.values(), key=lambda r: r["sku"])


def fmt_qty(reading):
    if reading is None:
        return "—"
    return str(reading["qty"])


def card_html(rec):
    meta = RULE_META.get(rec["rule"], {"label": rec["rule"], "tone": "standby", "stamp": rec["action"]})
    w = rec.get("warehouse_reading")
    m = rec.get("marketplace_reading")
    diff = None
    if w and m:
        diff = abs(w["qty"] - m["qty"])

    diff_html = f'<div class="diff">Δ {diff}</div>' if diff not in (None, 0) else ""

    return f"""
    <article class="ticket tone-{meta['tone']}">
      <div class="ticket-head">
        <span class="sku">{rec['sku']}</span>
        <span class="stamp stamp-{meta['tone']}">{meta['stamp']}</span>
      </div>
      <div class="readings">
        <div class="reading">
          <span class="src-label">WAREHOUSE</span>
          <span class="qty">{fmt_qty(w)}</span>
        </div>
        <div class="reading">
          <span class="src-label">MARKETPLACE</span>
          <span class="qty">{fmt_qty(m)}</span>
        </div>
        {diff_html}
      </div>
      <div class="rule-row">
        <span class="rule-badge">{meta['label']}</span>
        <span class="action">{rec['action']}</span>
      </div>
      <p class="reason">{rec['reason']}</p>
      <div class="timestamp">logged {rec['timestamp']}</div>
    </article>
    """


def summary_counts(decisions):
    counts = {}
    for rec in decisions:
        counts[rec["rule"]] = counts.get(rec["rule"], 0) + 1
    return counts


def build_html(decisions):
    cards = "\n".join(card_html(rec) for rec in decisions)
    counts = summary_counts(decisions)
    flagged = sum(v for k, v in counts.items() if RULE_META.get(k, {}).get("tone") == "alert")
    corrected = sum(v for k, v in counts.items() if RULE_META.get(k, {}).get("stamp") == "AUTO-CORRECTED")
    matched = counts.get("IN_AGREEMENT", 0)
    standby = counts.get("SOURCE_UNAVAILABLE", 0)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Inventory Reconciliation — Manifest</title>
<style>
  @font-face {{ font-family: 'system-mono'; src: local('Consolas'), local('Menlo'), local('Courier New'); }}
  :root {{
    --bg: #12151a;
    --panel: #1b1f27;
    --panel-border: #2a2f3a;
    --text: #e8e6df;
    --text-dim: #8b93a1;
    --ok: #3ecf8e;
    --warn: #ffb020;
    --alert: #ff5d5d;
    --standby: #5b9dd9;
    --mono: 'Courier New', Consolas, Menlo, monospace;
    --sans: -apple-system, 'Segoe UI', Roboto, Arial, sans-serif;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    padding: 32px 24px 64px;
  }}
  header {{
    max-width: 1100px;
    margin: 0 auto 28px;
    border-bottom: 1px solid var(--panel-border);
    padding-bottom: 20px;
  }}
  .eyebrow {{
    font-family: var(--mono);
    letter-spacing: 0.12em;
    color: var(--text-dim);
    font-size: 12px;
    text-transform: uppercase;
  }}
  h1 {{
    margin: 6px 0 4px;
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }}
  .subtitle {{ color: var(--text-dim); font-size: 14px; }}
  .stats {{
    max-width: 1100px;
    margin: 0 auto 28px;
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
  }}
  .stat {{
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 6px;
    padding: 12px 18px;
    min-width: 120px;
  }}
  .stat .n {{ font-family: var(--mono); font-size: 22px; font-weight: 700; }}
  .stat .l {{ font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; }}
  .stat.ok .n {{ color: var(--ok); }}
  .stat.warn .n {{ color: var(--warn); }}
  .stat.alert .n {{ color: var(--alert); }}
  .stat.standby .n {{ color: var(--standby); }}

  .grid {{
    max-width: 1100px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 16px;
  }}
  .ticket {{
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-left: 4px solid var(--text-dim);
    border-radius: 6px;
    padding: 16px 18px;
  }}
  .ticket.tone-ok {{ border-left-color: var(--ok); }}
  .ticket.tone-warn {{ border-left-color: var(--warn); }}
  .ticket.tone-alert {{ border-left-color: var(--alert); }}
  .ticket.tone-standby {{ border-left-color: var(--standby); }}

  .ticket-head {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }}
  .sku {{ font-family: var(--mono); font-weight: 700; font-size: 15px; }}
  .stamp {{
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: 0.08em;
    padding: 3px 8px;
    border-radius: 3px;
    border: 1px solid currentColor;
  }}
  .stamp-ok {{ color: var(--ok); }}
  .stamp-warn {{ color: var(--warn); }}
  .stamp-alert {{ color: var(--alert); }}
  .stamp-standby {{ color: var(--standby); }}

  .readings {{
    display: flex;
    gap: 16px;
    align-items: baseline;
    margin-bottom: 12px;
    padding-bottom: 12px;
    border-bottom: 1px dashed var(--panel-border);
  }}
  .reading {{ display: block; min-width: 100px; }}
  .src-label {{ display: block; font-size: 10px; color: var(--text-dim); letter-spacing: 0.06em; }}
  .qty {{ display: block; font-family: var(--mono); font-size: 20px; font-weight: 700; margin-top: 2px; }}
  .diff {{ margin-left: auto; font-family: var(--mono); color: var(--text-dim); font-size: 13px; }}

  .rule-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
  .rule-badge {{ font-size: 11px; font-weight: 700; letter-spacing: 0.04em; }}
  .action {{ font-family: var(--mono); font-size: 11px; color: var(--text-dim); }}

  .reason {{ font-size: 13px; line-height: 1.5; color: var(--text-dim); margin: 0 0 10px; }}
  .timestamp {{ font-family: var(--mono); font-size: 10px; color: #4a5160; }}

  footer {{
    max-width: 1100px;
    margin: 32px auto 0;
    color: #4a5160;
    font-family: var(--mono);
    font-size: 11px;
  }}
</style>
</head>
<body>
  <header>
    <div class="eyebrow">Inventory Reconciliation Agent</div>
    <h1>Stock Manifest</h1>
    <div class="subtitle">Latest decision per SKU — generated {generated_at}</div>
  </header>

  <div class="stats">
    <div class="stat ok"><div class="n">{matched}</div><div class="l">Matched</div></div>
    <div class="stat warn"><div class="n">{corrected}</div><div class="l">Auto-corrected</div></div>
    <div class="stat alert"><div class="n">{flagged}</div><div class="l">Flagged for review</div></div>
    <div class="stat standby"><div class="n">{standby}</div><div class="l">Awaiting source</div></div>
  </div>

  <div class="grid">
    {cards}
  </div>

  <footer>logs/decisions.jsonl · regenerate with `python generate_dashboard.py`</footer>
</body>
</html>
"""


if __name__ == "__main__":
    decisions = load_latest_decisions()
    if not decisions:
        print("No decisions found in logs/decisions.jsonl -- run `python demo.py` or `python agent.py --once` first.")
    else:
        html = build_html(decisions)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Dashboard written to {OUT_PATH} -- open it in a browser.")


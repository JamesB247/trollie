# ruff: noqa: E501 - HTML and SVG template strings read better unwrapped
"""Foot traffic and per-store behaviour for one crowd run, as data and as a standalone page.

The run is one compressed shopping day; every number here is in simulated hours.
"""

import html
import statistics
from collections import Counter, defaultdict

from scripts.crowd.actions import Toolbox
from scripts.crowd.api import BREACH, BUG, FRICTION, OK, REFUSED, Log

STORE_NAMES = {
    "ubuntu": "Ubuntu Hypermarket",
    "zest": "Zest Express",
    "fairbasket": "Fairbasket",
    "kaya": "Kaya Living",
    "bargainbox": "BargainBox Direct",
}
HOSTILE = {"malicious", "fraudster", "hijacker"}


def _pct(xs: list[int], q: float) -> int:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * q))] if xs else 0


def traffic(log: Log, tb: Toolbox, minutes: float) -> dict:
    hours = range(24)
    in_app = [0] * 24
    hostile_in_app = [0] * 24
    for opened, closed, archetype in tb.sessions:
        for h in hours:
            if opened < h + 1 and closed >= h:
                in_app[h] += 1
                hostile_in_app[h] += archetype in HOSTILE
    actions = [Counter() for _ in hours]
    orders_by_store = defaultdict(lambda: [0] * 24)
    complaints = [0] * 24
    stores: dict[str, dict] = defaultdict(lambda: defaultdict(list))
    for e in log.events:
        h = min(23, int(e.hour))
        actions[h][e.verdict] += 1
        if e.action == "approve_order" and e.verdict == OK:
            for code in set(e.stores.split(",")) - {""}:
                orders_by_store[code][h] += 1
        if e.action == "claim_not_delivered":
            complaints[h] += 1
        for code in set(e.stores.split(",")) - {""}:
            st = stores[code]
            st["actions"].append(e.action)
            if e.action == "choose_quote" and e.ms:
                st["reserve_ms"].append(e.ms)
                st["reserve_ok"].append(e.verdict == OK)
            if e.action == "approve_order" and e.ms:
                st["order_ms"].append(e.ms)
            if e.verdict == FRICTION:
                st["friction"].append(e.code or e.detail[:40])
            if e.action == "claim_not_delivered":
                st["claims"].append(e.verdict)
    per_store = {}
    for code, st in stores.items():
        per_store[code] = {
            "name": STORE_NAMES.get(code, code),
            "actions": len(st["actions"]),
            "orders": sum(orders_by_store[code]),
            "reserve_p50_ms": _pct(st["reserve_ms"], 0.5),
            "reserve_p95_ms": _pct(st["reserve_ms"], 0.95),
            "reserve_max_ms": max(st["reserve_ms"], default=0),
            "reserve_success": (
                round(sum(st["reserve_ok"]) / len(st["reserve_ok"]), 3)
                if st["reserve_ok"]
                else None
            ),
            "friction_top": Counter(st["friction"]).most_common(4),
            "claims": len(st["claims"]),
        }
    return {
        "minutes": minutes,
        "in_app": in_app,
        "hostile_in_app": hostile_in_app,
        "actions": [dict(c) for c in actions],
        "orders_by_store": {k: v for k, v in orders_by_store.items()},
        "claims": complaints,
        "per_store": per_store,
        "latency_overall_ms": {
            "p50": _pct([e.ms for e in log.events if e.ms], 0.5),
            "p95": _pct([e.ms for e in log.events if e.ms], 0.95),
            "mean": round(statistics.fmean([e.ms for e in log.events if e.ms] or [0])),
        },
    }


# --- Standalone page -----------------------------------------------------------------

STORE_COLORS = {
    "ubuntu": "var(--s1)",
    "zest": "var(--s2)",
    "fairbasket": "var(--s3)",
    "kaya": "var(--s4)",
    "bargainbox": "var(--bad)",
}

CSS = """
:root { --bg:#f6f7f5; --panel:#ffffff; --fg:#1d2321; --muted:#5d6a65; --rule:#d9dfdc;
  --s1:#2f6f8f; --s2:#c07a1a; --s3:#3f8a4d; --s4:#7a5aa6; --bad:#c2410c; --good:#2f7d4f;
  --body:"IBM Plex Sans",system-ui,sans-serif; --mono:"IBM Plex Mono",ui-monospace,monospace; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#121615; --panel:#1a201e;
  --fg:#e6ebe8; --muted:#9aa8a2; --rule:#2c3532; --s1:#6fb0d0; --s2:#e2a24a; --s3:#78c287;
  --s4:#b39ae0; --bad:#f08a5d; --good:#6cc690; color-scheme:dark } }
:root[data-theme="dark"] { --bg:#121615; --panel:#1a201e; --fg:#e6ebe8; --muted:#9aa8a2;
  --rule:#2c3532; --s1:#6fb0d0; --s2:#e2a24a; --s3:#78c287; --s4:#b39ae0; --bad:#f08a5d;
  --good:#6cc690; color-scheme:dark }
body { background:var(--bg); color:var(--fg); font-family:var(--body); line-height:1.5;
  padding-left:max(16px, env(safe-area-inset-left, 0px));
  padding-right:max(16px, env(safe-area-inset-right, 0px)); padding-block:24px; }
main { max-width:1100px; margin:0 auto; display:grid; gap:28px; }
h1 { font-size:1.6rem; margin:0; text-wrap:balance } h2 { font-size:1.1rem; margin:0 0 8px }
.sub { color:var(--muted); margin:4px 0 0 } .num { font-variant-numeric:tabular-nums; font-family:var(--mono) }
section { background:var(--panel); border:1px solid var(--rule); border-radius:8px; padding:16px; min-width:0 }
.grid { display:grid; gap:16px; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)) }
.scroll { overflow-x:auto } table { border-collapse:collapse; width:100%; font-size:.9rem }
th, td { text-align:left; padding:6px 8px; border-bottom:1px solid var(--rule); vertical-align:top }
th { color:var(--muted); font-weight:600; font-size:.8rem; text-transform:uppercase; letter-spacing:.04em }
.pass { color:var(--good); font-weight:600 } .fail { color:var(--bad); font-weight:600 }
.key { display:flex; flex-wrap:wrap; gap:12px; font-size:.85rem; color:var(--muted) }
.key span::before { content:""; display:inline-block; width:10px; height:10px; margin-right:6px;
  border-radius:2px; background:var(--c) }
svg text { fill:var(--muted); font-size:11px; font-family:var(--mono) }
"""


def _bars(
    values: list[int], color: str, height: int = 160, overlay: list[int] | None = None
) -> str:
    w, pad, left = 720, 24, 34
    top = max(1, max(values + (overlay or []), default=1))
    bw = (w - left - 8) / 24
    parts = []
    for tick in (0, top // 2, top):
        y = height - pad - (height - 2 * pad) * tick / top
        parts.append(
            f'<line x1="{left}" x2="{w - 8}" y1="{y:.1f}" y2="{y:.1f}" stroke="var(--rule)"/>'
        )
        parts.append(f'<text x="{left - 6}" y="{y + 4:.1f}" text-anchor="end">{tick}</text>')
    for h, v in enumerate(values):
        bh = (height - 2 * pad) * v / top
        x = left + h * bw + 2
        parts.append(
            f'<rect x="{x:.1f}" y="{height - pad - bh:.1f}" width="{bw - 4:.1f}" height="{bh:.1f}" '
            f'fill="{color}" rx="2"><title>{h:02d}:00 - {v}</title></rect>'
        )
        if overlay:
            oh = (height - 2 * pad) * overlay[h] / top
            parts.append(
                f'<rect x="{x:.1f}" y="{height - pad - oh:.1f}" width="{bw - 4:.1f}" '
                f'height="{oh:.1f}" fill="var(--bad)" rx="2"><title>hostile {overlay[h]}</title></rect>'
            )
        if h % 3 == 0:
            parts.append(
                f'<text x="{x + (bw - 4) / 2:.1f}" y="{height - 6}" text-anchor="middle">{h:02d}h</text>'
            )
    return f'<div class="scroll"><svg viewBox="0 0 {w} {height}" width="100%" role="img">{"".join(parts)}</svg></div>'


def _stacked(series: dict[str, list[int]], height: int = 180) -> str:
    w, pad, left = 720, 24, 34
    totals = [sum(v[h] for v in series.values()) for h in range(24)]
    top = max(1, max(totals, default=1))
    bw = (w - left - 8) / 24
    parts = []
    for tick in (0, top // 2, top):
        y = height - pad - (height - 2 * pad) * tick / top
        parts.append(
            f'<line x1="{left}" x2="{w - 8}" y1="{y:.1f}" y2="{y:.1f}" stroke="var(--rule)"/>'
        )
        parts.append(f'<text x="{left - 6}" y="{y + 4:.1f}" text-anchor="end">{tick}</text>')
    for h in range(24):
        base = height - pad
        x = left + h * bw + 2
        for code, vals in series.items():
            bh = (height - 2 * pad) * vals[h] / top
            if bh:
                parts.append(
                    f'<rect x="{x:.1f}" y="{base - bh:.1f}" width="{bw - 4:.1f}" height="{bh:.1f}" '
                    f'fill="{STORE_COLORS.get(code, "var(--muted)")}"><title>{STORE_NAMES.get(code, code)} '
                    f"{h:02d}:00 - {vals[h]}</title></rect>"
                )
                base -= bh
        if h % 3 == 0:
            parts.append(
                f'<text x="{x + (bw - 4) / 2:.1f}" y="{height - 6}" text-anchor="middle">{h:02d}h</text>'
            )
    return f'<div class="scroll"><svg viewBox="0 0 {w} {height}" width="100%" role="img">{"".join(parts)}</svg></div>'


def traffic_html(summary: dict) -> str:
    t = summary["traffic"]
    e = html.escape
    key = "".join(
        f'<span style="--c:{STORE_COLORS.get(c, "var(--muted)")}">{e(STORE_NAMES.get(c, c))}</span>'
        for c in t["orders_by_store"]
    )
    rows = []
    facts = summary["oracle_facts"].get("per_store", {})
    for code, st in sorted(t["per_store"].items(), key=lambda kv: -kv[1]["actions"]):
        f = facts.get(code, {})
        succ = st["reserve_success"]
        rows.append(
            "<tr>"
            f"<td>{e(st['name'])}<br><span class='sub'>{e(str(f.get('risk_tier', '')))} · {e(str(f.get('state', '')))}</span></td>"
            f"<td class='num'>{st['orders']}</td>"
            f"<td class='num'>{st['reserve_p50_ms']} / {st['reserve_p95_ms']} / {st['reserve_max_ms']}</td>"
            f"<td class='num'>{'' if succ is None else f'{succ:.0%}'}</td>"
            f"<td class='num'>R{f.get('paid_minor', 0) / 100:,.0f}</td>"
            f"<td class='num'>{f.get('delivered', 0)} / {f.get('paid_legs', 0)}</td>"
            f"<td class='num'>{f.get('overdue', 0)}</td>"
            f"<td class='num'>R{f.get('refunded_minor', 0) / 100:,.0f}</td>"
            f"<td class='num'>R{f.get('stranded_minor', 0) / 100:,.0f}</td>"
            "</tr>"
        )
    checks = "".join(
        f"<tr><td>{e(c['name'])}</td><td class='{'pass' if c['ok'] else 'fail'}'>"
        f"{'Pass' if c['ok'] else 'Fail'}</td><td>{e(c['detail'][:260])}</td></tr>"
        for c in summary["oracle"]
    )
    timeline = "".join(
        f"<tr><td class='num'>{h:05.2f}h</td><td>{e(what)}</td></tr>"
        for h, what in summary["round2"]["timeline"]
    )
    v = summary["verdicts"]
    stamp = (
        f"{summary['users']} shoppers · one simulated day in {summary['minutes']:g} minutes · "
        f"seed {summary['seed']} · {summary['actions']} actions · "
        f"{v.get(OK, 0)} ok, {v.get(FRICTION, 0)} blocked, {v.get(REFUSED, 0)} attacks refused, "
        f"{v.get(BREACH, 0)} breaches, {v.get(BUG, 0)} server errors"
    )
    return f"""<title>Trollie Crowd Day</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&display=swap">
<style>{CSS}</style>
<main>
<header><h1>Trollie crowd day</h1><p class="sub">{e(stamp)}. SIMULATED, NOT REAL MONEY.</p></header>
<section><h2>Foot traffic: shoppers with the app open</h2>
<div class="key"><span style="--c:var(--s1)">All shoppers</span><span style="--c:var(--bad)">Fraudsters and attackers</span></div>
{_bars(t["in_app"], "var(--s1)", overlay=t["hostile_in_app"])}</section>
<section><h2>Orders placed, by store and hour</h2><div class="key">{key}</div>
{_stacked(t["orders_by_store"])}</section>
<section><h2>Stores</h2><div class="scroll"><table>
<tr><th>Store</th><th>Orders</th><th>Stock hold ms p50 / p95 / max</th><th>Hold succeeded</th>
<th>Paid</th><th>Delivered / paid legs</th><th>Overdue</th><th>Refunded</th><th>Paid, nothing received</th></tr>
{"".join(rows)}</table></div></section>
<section><h2>Money and safety checks</h2><div class="scroll"><table>
<tr><th>Check</th><th>Result</th><th>Detail</th></tr>{checks}</table></div></section>
<section><h2>What happened when</h2><div class="scroll"><table>
<tr><th>Time</th><th>Event</th></tr>{timeline or "<tr><td colspan=2>Nothing notable.</td></tr>"}</table></div></section>
</main>"""

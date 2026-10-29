"""Turn a before run and an after run into the data files behind the crowd-day dashboard.

    uv run python -m scripts.crowd.dashboard_data sim_runs/day1-before sim_runs/day2-after OUT

Writes traffic.json, store_hours.json, stores.json, scenarios.json, checks.json and
timeline.json into OUT. SIMULATED — NOT REAL MONEY.
"""

import json
import sys
from pathlib import Path

from scripts.crowd.traffic import STORE_NAMES

RUNS = ("Before controls", "After controls")


def load(path: str) -> dict:
    return json.loads((Path(path) / "summary.json").read_text())


def rand(minor) -> float:
    return round((minor or 0) / 100, 2)


def main(before_dir: str, after_dir: str, out_dir: str) -> None:
    runs = dict(zip(RUNS, (load(before_dir), load(after_dir)), strict=True))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    traffic, store_hours, stores, timeline = [], [], [], []
    for run, s in runs.items():
        t = s["traffic"]
        orders_by_hour = [sum(v[h] for v in t["orders_by_store"].values()) for h in range(24)]
        for h in range(24):
            traffic.append(
                {
                    "run": run,
                    "hour": h,
                    "shoppers_in_app": t["in_app"][h],
                    "fraud_and_attackers_in_app": t["hostile_in_app"][h],
                    "orders": orders_by_hour[h],
                }
            )
            for code, vals in t["orders_by_store"].items():
                store_hours.append(
                    {"run": run, "hour": h, "store": STORE_NAMES.get(code, code), "orders": vals[h]}
                )
        facts = s["oracle_facts"].get("per_store", {})
        for code, f in facts.items():
            tp = t["per_store"].get(code, {})
            stores.append(
                {
                    "run": run,
                    "store": STORE_NAMES.get(code, code),
                    "tier": f.get("risk_tier"),
                    "state_at_end": f.get("state"),
                    "orders": tp.get("orders", 0),
                    "paid_rand": rand(f.get("paid_minor")),
                    "paid_legs": f.get("paid_legs", 0),
                    "delivered_legs": f.get("delivered", 0),
                    "overdue_legs": f.get("overdue", 0),
                    "refunded_rand": rand(f.get("refunded_minor")),
                    "paid_nothing_received_rand": rand(f.get("stranded_minor")),
                    "hold_p95_ms": tp.get("reserve_p95_ms", 0),
                    "hold_max_ms": tp.get("reserve_max_ms", 0),
                    "hold_success": tp.get("reserve_success"),
                }
            )
        for hour, what in s["round2"]["timeline"]:
            timeline.append(
                {"id": f"{run[:1]}{len(timeline) + 1}", "run": run, "hour": round(min(hour, 28), 2),
                 "event": what}
            )  # fmt: skip

    b, a = runs["Before controls"], runs["After controls"]

    def check(s, name):
        return next((c for c in s["oracle"] if c["name"] == name), {"ok": None, "detail": ""})

    def stranded(s):
        return rand(
            sum(f.get("stranded_minor", 0) for f in s["oracle_facts"]["per_store"].values())
        )

    def scam(s, key):
        return rand(s["oracle_facts"]["per_store"].get("bargainbox", {}).get(key, 0))

    def agent_suspensions(s):
        return s["oracle_facts"].get("incidents", {}).get("agent_suspended", 0)

    scenarios = [
        ("Paid, nothing received (all stores)", "rand", stranded(b), stranded(a)),
        ("Paid to the scam store", "rand", scam(b, "paid_minor"), scam(a, "paid_minor")),
        ("Refunded to scam-store customers", "rand",
         scam(b, "refunded_minor"), scam(a, "refunded_minor")),
        ("Stolen money loaded", "rand", rand(b["round2"]["stolen_loaded_minor"]),
         rand(a["round2"]["stolen_loaded_minor"])),
        ("Stolen money spent before the bank recalled it", "rand",
         rand(b["oracle_facts"]["stolen_funds"]["unrecovered_after_reversal_minor"]),
         rand(a["oracle_facts"]["stolen_funds"]["unrecovered_after_reversal_minor"])),
        ("Hijacked-agent baskets owners paid for", "rand",
         rand(b["oracle_facts"]["hijack"]["spend_minor"]),
         rand(a["oracle_facts"]["hijack"]["spend_minor"])),
        ("Stolen agents", "count", b["oracle_facts"]["hijack"].get("stolen_agents", 0),
         a["oracle_facts"]["hijack"].get("stolen_agents", 0)),
        ("Stolen agents suspended", "count",
         b["oracle_facts"]["hijack"].get("stolen_agents_suspended", 0),
         a["oracle_facts"]["hijack"].get("stolen_agents_suspended", 0)),
        ("Agents suspended in total", "count", agent_suspensions(b), agent_suspensions(a)),
        ("Orders placed", "count", b["orders"], a["orders"]),
        ("Server errors", "count", b["verdicts"].get("BUG", 0), a["verdicts"].get("BUG", 0)),
        ("Rule breaches", "count", b["verdicts"].get("BREACH", 0), a["verdicts"].get("BREACH", 0)),
    ]  # fmt: skip
    scenario_rows = [
        {"scenario": n, "unit": u, "before": bv, "after": av} for n, u, bv, av in scenarios
    ]
    checks = [
        {
            "check": c["name"],
            "before": "Pass" if check(b, c["name"])["ok"] else "Fail",
            "after": "Pass" if c["ok"] else "Fail",
            "after_detail": c["detail"][:240],
        }
        for c in a["oracle"]
    ]
    for name, rows in {
        "traffic": traffic,
        "store_hours": store_hours,
        "stores": stores,
        "scenarios": scenario_rows,
        "checks": checks,
        "timeline": timeline,
    }.items():
        (out / f"{name}.json").write_text(json.dumps(rows, indent=1))
    print(
        f"wrote {len(traffic)} traffic, {len(stores)} store, {len(timeline)} timeline rows to {out}"
    )


if __name__ == "__main__":
    main(*sys.argv[1:4])

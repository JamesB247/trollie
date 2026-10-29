"""Run the crowd. SIMULATED — NOT REAL MONEY.

    uv run python -m scripts.crowd.run --spawn-server --users 60 --minutes 8
    uv run python -m scripts.crowd.run --base-url http://localhost:8000 --database-url ...
    uv run python -m scripts.crowd.run --spawn-server --brain mixed     # needs ANTHROPIC_API_KEY

Writes events.jsonl, summary.json and REPORT.md into --out (default sim_runs/<timestamp>).
"""

import argparse
import asyncio
import json
import os
import random
import secrets
import socket
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import httpx
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.seed import sid
from app.simulators.bigmarket import CHAINS as BIG_CHAINS
from app.simulators.bigmarket import location_id as big_location_id
from app.simulators.market import CHAINS
from scripts.crowd.actions import Board, Shopper, Toolbox
from scripts.crowd.api import BREACH, BUG, FRICTION, OK, SLOW, Api, Log
from scripts.crowd.brains import StochasticBrain, make_brain
from scripts.crowd.oracle import audit, scenario_facts
from scripts.crowd.personas import draw_crowd
from scripts.crowd.traffic import traffic, traffic_html
from scripts.crowd.world import World

ADMIN_URL = "postgresql+psycopg://trollie:trollie@localhost:5432/trollie_test"
CROWD_DB = "postgresql+psycopg://trollie:trollie@localhost:5432/trollie_crowd"


def spawn(database_url: str, log_path: Path) -> tuple[subprocess.Popen, str]:
    admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        if not conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname='trollie_crowd'")
        ).first():
            conn.execute(text("CREATE DATABASE trollie_crowd"))
    admin.dispose()
    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    engine.dispose()
    cfg = Config("alembic.ini")
    cfg.attributes["database_url"] = database_url
    cfg.attributes["environment"] = "test"
    command.upgrade(cfg, "head")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://localhost:{port}"
    env = {
        **os.environ,
        "TROLLIE_ENV": "test",
        "TROLLIE_DATABASE_URL": database_url,
        "TROLLIE_RUN_WORKER": "true",
        "TROLLIE_WEBAUTHN_RP_ID": "localhost",
        "TROLLIE_WEBAUTHN_ORIGIN": base,
        # Time-based controls follow the compressed day (20 minutes = 24 hours).
        "TROLLIE_DELIVERY_GRACE_MINUTES": "2",
        "TROLLIE_WALLET_CLEARING_MINUTES": "6",
        "TROLLIE_AGENT_STRIKE_WINDOW_MINUTES": "10",
    }
    out = open(log_path, "w")  # noqa: SIM115 - lives as long as the server
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:create_app", "--factory",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        env=env, stdout=out, stderr=subprocess.STDOUT,
    )  # fmt: skip
    for _ in range(200):
        try:
            if httpx.get(f"{base}/healthz", timeout=0.5).status_code == 200:
                return proc, base
        except httpx.HTTPError:
            time.sleep(0.1)
    proc.kill()
    raise RuntimeError(f"server did not start; see {log_path}")


# Relative shopping intensity per hour of a South African day for an online grocer: quiet
# night, morning trickle, lunch bump, evening peak after work. Illustrative, not measured.
HOUR_WEIGHTS = [0.15, 0.1, 0.08, 0.08, 0.1, 0.25, 0.5, 0.7, 0.8, 0.9, 1.0, 1.1,
                1.3, 1.2, 0.9, 0.9, 1.1, 1.6, 2.0, 1.9, 1.5, 1.0, 0.6, 0.3]  # fmt: skip
# Fraud is busiest when people sleep.
NIGHT_WEIGHTS = [1.6, 1.8, 1.8, 1.5, 1.0, 0.6, 0.4, 0.4, 0.5, 0.5, 0.5, 0.5,
                 0.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4]  # fmt: skip


def schedule(s: Shopper, day_s: float) -> list[tuple[float, int]]:
    """Sessions as (offset seconds from the start of the run, number of actions)."""
    rng = s.p.rng
    key = s.p.archetype.key
    hostile = key in ("malicious", "fraudster", "hijacker")
    n = rng.randint(4, 7) if hostile else rng.choices([1, 2, 3, 4], [3, 4, 3, 2])[0]
    weights = NIGHT_WEIGHTS if hostile else HOUR_WEIGHTS
    out = []
    for _ in range(n):
        hour = rng.choices(range(24), weights)[0] + rng.random()
        out.append((hour / 24 * day_s, rng.randint(4, 14)))
    if key in ("delegator", "stokvel", "household", "careful", "furniture", "broke"):
        # Most people come back later in the day to see where their order is.
        out.append((rng.uniform(0.6, 0.97) * day_s, rng.randint(1, 3)))
    return sorted(out)


async def live(s: Shopper, tb: Toolbox, brain, start: float, day_s: float, speed: float, stats):
    rng = s.p.rng
    sessions = schedule(s, day_s)
    onboarded = False
    for offset, actions in sessions:
        wait = start + offset - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        if time.monotonic() > start + day_s:
            break
        if not onboarded:
            try:
                await tb.onboard(s)
                onboarded = True
            except Exception as exc:  # noqa: BLE001
                stats["onboard_failures"].append(f"{s.name}: {exc}")
                return
        tb.session_opened(s)
        try:
            await brain.session_start(s, tb)
        except Exception as exc:  # noqa: BLE001
            stats["harness_errors"].append(f"{s.name}: {type(exc).__name__}: {exc}")
        for _ in range(actions):
            await asyncio.sleep(rng.expovariate(1 / s.p.archetype.mean_think_s) * speed)
            try:
                await brain.step(s, tb)
            except Exception as exc:  # noqa: BLE001 - a harness error is recorded, not fatal
                stats["harness_errors"].append(f"{s.name}: {type(exc).__name__}: {exc}")
        tb.session_closed(s)


async def main_async(args) -> int:
    seed = args.seed if args.seed is not None else secrets.randbits(48)
    rng = random.Random(seed)
    out = Path(args.out or f"sim_runs/{datetime.now(UTC):%Y%m%d-%H%M%S}")
    out.mkdir(parents=True, exist_ok=True)
    proc = None
    base, db_url = args.base_url, args.database_url
    if args.spawn_server:
        db_url = CROWD_DB
        proc, base = spawn(db_url, out / "server.log")
    print(f"seed {seed}  server {base}  output {out}")
    api = Api(base)
    try:
        large = args.market == "large"
        t0 = time.monotonic()
        seeded = await api.must("POST", "/v1/dev/seed", params={"market": args.market}, timeout=600)
        print(f"seeded in {time.monotonic() - t0:.0f}s: {seeded.get('large_market')}")
        # Merchant faults target a branch (location id); the seed's ids are deterministic.
        if large:
            loc_ids = [str(big_location_id(b.code)) for c in BIG_CHAINS for b in c.branches]
        else:
            loc_ids = [str(sid("location", b.code)) for c in CHAINS for b in c.branches]

        day_s = args.minutes * 60
        log, board = Log(day_seconds=day_s), Board()
        tb = Toolbox(api, log, board)
        crowd = draw_crowd(args.users, rng, large=large)
        shoppers = [Shopper(p) for p in crowd]
        brains = [make_brain(s, args.brain, rng) for s in shoppers]
        mix = Counter(s.p.archetype.label for s in shoppers)
        print("crowd:", ", ".join(f"{k} x{v}" for k, v in mix.most_common()))
        world = World(api, board, random.Random(rng.getrandbits(64)), args.chaos, log)
        stop = asyncio.Event()
        start = time.monotonic()
        deadline = start + day_s
        stats = defaultdict(list)
        world_task = asyncio.create_task(world.run(stop, loc_ids, start + 0.3 * day_s))
        progress = asyncio.create_task(_progress(log, deadline, tb))
        await asyncio.gather(
            *[
                live(s, tb, b, start, day_s, args.speed, stats)
                for s, b in zip(shoppers, brains, strict=True)
            ]
        )
        # The night after: couriers finish (or don't), then people check what arrived.
        await asyncio.sleep(max(0, deadline - time.monotonic()) + args.tail_minutes * 60)
        for s, b in zip(shoppers, brains, strict=True):
            if s.orders:
                await b.session_start(s, tb)
        # Let the world finish deliveries and transfers, then stop the chaos and settle.
        await asyncio.sleep(10)
        await api.call("DELETE", "/v1/dev/sim/faults")
        await asyncio.sleep(20)
        stop.set()
        progress.cancel()
        await asyncio.gather(world_task, return_exceptions=True)
        # Payments still waiting on a webhook are looked up after two quiet minutes (I-041);
        # give that time to happen so the audit sees settled state, not webhooks in transit.
        for _ in range(15):
            await api.call("POST", "/v1/dev/pump")
            await asyncio.sleep(10)
        await api.call("POST", "/v1/dev/settlement-reports")
        tb_resp = await api.must("GET", "/v1/dev/ledger/trial-balance")
        sent = {s.account_id: s.topups_sent_minor for s in shoppers if s.account_id}
        oracle = audit(db_url, sent, tb_resp)
        hijacks = [(v.account_id, when) for v, _, when in board.hijacked]
        scenario = scenario_facts(db_url, grace_s=StochasticBrain.grace_s, hijacks=hijacks)
        oracle.checks += scenario.checks
        oracle.facts |= scenario.facts
        log.dump(out / "events.jsonl")
        summary = summarise(seed, args, shoppers, log, world, oracle, stats, out)
        summary["traffic"] = traffic(log, tb, args.minutes)
        summary["round2"] = {
            "hijacks": [(v.name, th.name) for v, th, _ in board.hijacked],
            "hijack_requests_sent": board.hijack_requests,
            "stolen_loaded_minor": board.stolen_minor,
            "timeline": world.timeline,
            "seeded": seeded.get("large_market"),
        }
        (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
        (out / "REPORT.md").write_text(render(summary))
        (out / "traffic.html").write_text(traffic_html(summary))
        print(render(summary))
        return 1 if summary["critical_failures"] or summary["verdicts"].get(BREACH) else 0
    finally:
        await api.close()
        if proc:
            proc.terminate()
            proc.wait(timeout=15)


async def _progress(log: Log, deadline: float, tb: Toolbox) -> None:
    while True:
        await asyncio.sleep(30)
        left = max(0, int(deadline - time.monotonic()))
        c = Counter(e.verdict for e in log.events)
        print(
            f"  sim {log.hour():05.2f}h  in app {len(tb.online)}  {len(log.events)} actions, "
            f"{left}s left: {dict(c)}",
            flush=True,
        )


def summarise(seed, args, shoppers, log: Log, world: World, oracle, stats, out) -> dict:
    ev = log.events
    verdicts = Counter(e.verdict for e in ev)
    by_arch = defaultdict(Counter)
    for e in ev:
        by_arch[e.archetype][e.verdict] += 1
    friction = Counter()
    for e in ev:
        if e.verdict == FRICTION:
            friction[_bucket(e)] += 1
    attacks = defaultdict(Counter)
    for e in ev:
        if e.archetype == "malicious" or e.said.startswith("[attack"):
            attacks[e.action][e.verdict] += 1
    quotes = [e for e in ev if e.action == "get_quotes" and e.verdict == OK]
    two_store = sum("2 stores" in e.detail for e in quotes)
    latencies = sorted(e.ms for e in ev if e.ms)
    no_basket = Counter(
        k.strip("[]'")
        for e in ev
        if e.action == "get_quotes" and e.verdict == FRICTION
        for k in e.detail.split("]")[0].split("[")[-1].split(", ")
    )
    return {
        "seed": seed,
        "users": len(shoppers),
        "minutes": args.minutes,
        "brain": args.brain,
        "chaos": args.chaos,
        "crowd": Counter(s.p.archetype.label for s in shoppers),
        "zones": Counter(s.p.zone for s in shoppers),
        "models": Counter(s.p.model or "stochastic" for s in shoppers),
        "actions": len(ev),
        "verdicts": dict(verdicts),
        "by_archetype": {k: dict(v) for k, v in by_arch.items()},
        "friction": friction.most_common(25),
        "no_basket_reasons": dict(no_basket),
        "attacks": {k: dict(v) for k, v in sorted(attacks.items())},
        "breaches": [asdict(e) for e in ev if e.verdict == BREACH],
        "bugs": [asdict(e) for e in ev if e.verdict == BUG][:40],
        "slow": [asdict(e) for e in ev if e.verdict == SLOW][:20],
        "quotes_ok": len(quotes),
        "quotes_two_store": two_store,
        "orders": sum(len(s.orders) for s in shoppers),
        "latency_ms": {
            "p50": _pct(latencies, 0.5),
            "p95": _pct(latencies, 0.95),
            "p99": _pct(latencies, 0.99),
            "max": latencies[-1] if latencies else 0,
        },
        "world": {
            "faults_armed": Counter(world.faults_armed),
            "deliveries": world.deliveries,
            "bank_transfers": world.transfers_sent,
            "settlement_runs": len(world.settlements),
            "errors": world.errors[:20],
        },
        "oracle": [asdict(c) for c in oracle.checks],
        "oracle_facts": oracle.facts,
        "critical_failures": [
            c.name for c in oracle.checks if not c.ok and c.severity == "critical"
        ],
        "harness": {k: v[:20] for k, v in stats.items()},
        "chat_messages_unhandled": sum(1 for e in ev if e.action == "chat"),
        "out": str(out),
    }


def _bucket(e) -> str:
    d = e.detail
    if e.action == "search":
        return "search: " + ("item not sold anywhere" if "not sold" in d else "word not recognised")
    if e.action == "get_quotes":
        return "quote: " + d.split("]")[0].split("[")[-1]
    return f"{e.action}: {e.code or d[:60]}"


def _pct(xs, q):
    return xs[min(len(xs) - 1, int(len(xs) * q))] if xs else 0


def render(s: dict) -> str:
    v = s["verdicts"]
    lines = [
        "# Crowd simulation report — SIMULATED, NOT REAL MONEY",
        "",
        f"Seed `{s['seed']}` · {s['users']} shoppers · {s['minutes']} min · brain "
        f"`{s['brain']}` · chaos {s['chaos']}",
        "",
        "Crowd: " + ", ".join(f"{k} ×{n}" for k, n in s["crowd"].items()),
        "",
        f"**{s['actions']} actions**: " + ", ".join(f"{k} {n}" for k, n in sorted(v.items())),
        f"Quotes produced {s['quotes_ok']} ({s['quotes_two_store']} used two stores) · orders "
        f"{s['orders']} · latency p50 {s['latency_ms']['p50']} ms, p95 "
        f"{s['latency_ms']['p95']} ms, max {s['latency_ms']['max']} ms",
        "",
        "## Invariants (checked in the database after the run)",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for c in s["oracle"]:
        mark = "PASS" if c["ok"] else ("**FAIL**" if c["severity"] == "critical" else "warn")
        lines.append(f"| {c['name']} | {mark} | {c['detail'][:300]} |")
    lines += ["", "## Attacks", "", "| Technique | Outcomes |", "|---|---|"]
    for k, outcomes in s["attacks"].items():
        lines.append(f"| {k} | " + ", ".join(f"{a} {n}" for a, n in outcomes.items()) + " |")
    lines += ["", "## Breaches", ""]
    lines += [f"- {b['user']} `{b['action']}`: {b['detail']}" for b in s["breaches"]] or ["None."]
    lines += ["", "## Server errors and bugs", ""]
    lines += [
        f"- {b['user']} ({b['archetype']}) `{b['action']}`: {b['detail'][:300]}" for b in s["bugs"]
    ] or ["None."]
    lines += ["", "## Where honest shoppers got stuck", "", "| Friction | Count |", "|---|---|"]
    lines += [f"| {k} | {n} |" for k, n in s["friction"]]
    lines += [
        "",
        f"Chat messages with nowhere to go: {s['chat_messages_unhandled']}",
        "",
        "## By archetype",
        "",
        "| Archetype | Outcomes |",
        "|---|---|",
    ]
    lines += [
        f"| {k} | " + ", ".join(f"{a} {n}" for a, n in sorted(o.items())) + " |"
        for k, o in sorted(s["by_archetype"].items())
    ]
    lines += [
        "",
        "## World",
        "",
        f"Faults injected: {dict(s['world']['faults_armed'])}",
        f"Deliveries: {s['world']['deliveries']} · bank transfers {s['world']['bank_transfers']}"
        f" · settlement runs {s['world']['settlement_runs']}",
        f"Order states: {s['oracle_facts'].get('orders_by_state')}",
        f"Attention reasons: {s['oracle_facts'].get('attention_reasons')}",
        f"Incidents: {s['oracle_facts'].get('incidents')}",
        f"World errors: {s['world']['errors'] or 'none'}",
        f"Harness: {s['harness'] or 'clean'}",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument(
        "--database-url", default="postgresql+psycopg://trollie:trollie@localhost:5432/trollie"
    )
    ap.add_argument("--spawn-server", action="store_true")
    ap.add_argument("--users", type=int, default=60)
    ap.add_argument("--minutes", type=float, default=20, help="one simulated day")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--brain", choices=["stochastic", "claude", "mixed"], default="stochastic")
    ap.add_argument("--chaos", type=float, default=0.5, help="chance per tick of a fault")
    ap.add_argument("--market", choices=["small", "large"], default="large")
    ap.add_argument("--tail-minutes", type=float, default=4, help="after the day: deliveries")
    ap.add_argument("--speed", type=float, default=1.0, help="<1 compresses pauses")
    ap.add_argument("--out")
    sys.exit(asyncio.run(main_async(ap.parse_args())))


if __name__ == "__main__":
    main()

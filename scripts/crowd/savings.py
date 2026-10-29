"""Does splitting a basket across two stores save money in the synthetic market?

    uv run python -m scripts.crowd.savings --database-url URL [--baskets 200]

For random household baskets in every zone, compares the cheapest complete basket from one
store, from up to two stores, and the naive "lowest shelf price per item anywhere" figure a
price-comparison site would show. Runs the real optimiser on the real seeded data. Prices
are invented, so the numbers describe this fixture, not South African retail.
"""

import argparse
import dataclasses
import random
import secrets
import statistics
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.quotes.inputs import build_problem
from app.quotes.optimiser import Candidate, LineRequest, Quantity, Rule, Strategy, optimise
from app.seed import sid
from app.simulators.market import GROCERY, MARKET_PRODUCTS, MARKET_ZONES, REGIONS


def basket(rng: random.Random) -> list[LineRequest]:
    pool = [p for p in MARKET_PRODUCTS if p.category in GROCERY]
    picks = rng.sample(pool, rng.randint(5, 15))
    return [
        LineRequest(
            line_id=p.code,
            rule=Rule.FLEXIBLE,
            candidates=(Candidate(sid("product", p.code)),),
            quantity=Quantity(packs=rng.choices([1, 2, 3], [6, 3, 1])[0]),
        )
        for p in picks
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", required=True)
    ap.add_argument("--baskets", type=int, default=200)
    ap.add_argument("--seed", type=int)
    args = ap.parse_args()
    seed = args.seed if args.seed is not None else secrets.randbits(32)
    rng = random.Random(seed)
    engine = create_engine(args.database_url)
    now = datetime.now(UTC)
    region_of = {z: r for r, zones in REGIONS.items() for z in zones}
    rows = []
    with Session(engine) as s:
        for i in range(args.baskets):
            zone = MARKET_ZONES[i % len(MARKET_ZONES)]
            lines = basket(rng)
            problem = build_problem(s, lines=lines, zone=zone, now=now)
            one = optimise(dataclasses.replace(problem, max_stores=1)).options[Strategy.CHEAPEST]
            two = optimise(problem).options[Strategy.CHEAPEST]
            naive = 0
            for ln in lines:
                prices = [
                    o.price_minor
                    for o in problem.offers
                    if o.product_id == ln.candidates[0].product_id
                ]
                naive += min(prices) * ln.quantity.packs if prices else 0
            rows.append(
                {
                    "zone": zone,
                    "items": len(lines),
                    "one": one.total_minor if one else None,
                    "two": two.total_minor if two else None,
                    "two_legs": len(two.legs) if two else 0,
                    "naive_goods": naive,
                    "two_goods": two.goods_minor if two else None,
                }
            )
    engine.dispose()

    print(f"Split-basket savings in the synthetic market (seed {seed}, {len(rows)} baskets)\n")
    by_region: dict[str, list[dict]] = {}
    for r in rows:
        by_region.setdefault(region_of[r["zone"]], []).append(r)
    for region, rs in [("All", rows), *sorted(by_region.items())]:
        n = len(rs)
        single_ok = [r for r in rs if r["one"]]
        two_ok = [r for r in rs if r["two"]]
        both = [r for r in rs if r["one"] and r["two"]]
        split_used = [r for r in two_ok if r["two_legs"] == 2]
        saves = [(r["one"] - r["two"]) / r["one"] * 100 for r in both]
        split_saves = [(r["one"] - r["two"]) / r["one"] * 100 for r in both if r["two_legs"] == 2]
        rescued = [r for r in rs if r["two"] and not r["one"]]
        gap = [
            (r["two_goods"] - r["naive_goods"]) / r["naive_goods"] * 100
            for r in two_ok
            if r["naive_goods"]
        ]
        print(f"## {region} ({n} baskets)")
        print(f"  complete from ONE store:        {len(single_ok) / n:6.1%}")
        print(f"  complete from up to TWO stores: {len(two_ok) / n:6.1%}  "
              f"(two stores rescued {len(rescued)} baskets one store could not fill)")  # fmt: skip
        print(f"  cheapest option used two stores: {len(split_used) / max(1, len(two_ok)):6.1%}")
        if saves:
            print(f"  saving vs best single store: median {statistics.median(saves):.1f}%, "
                  f"max {max(saves):.1f}%; when split is chosen: median "
                  f"{statistics.median(split_saves) if split_saves else 0:.1f}%")  # fmt: skip
        if gap:
            print(f"  real goods cost above 'cheapest shelf price anywhere': median "
                  f"{statistics.median(gap):.1f}% (that headline is not achievable)")  # fmt: skip
        print()


if __name__ == "__main__":
    main()

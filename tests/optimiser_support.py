"""Fixture builder and an independent brute-force oracle for the optimiser.

The oracle shares only the per-line pricing rules (price_line/units_for, tested on their
own); store-set enumeration, assignment, stock, minimums, thresholds and slot choice are
re-implemented by exhaustive search.
"""

import itertools
import uuid
from datetime import UTC, datetime, timedelta

from app.quotes.optimiser import (
    Candidate,
    LineRequest,
    Location,
    Offer,
    Problem,
    ProductInfo,
    Promo,
    Quantity,
    Rule,
    Slot,
    price_line,
    units_for,
)

NOW = datetime(2026, 11, 2, 8, 0, tzinfo=UTC)


class World:
    def __init__(self) -> None:
        self.products: dict[uuid.UUID, ProductInfo] = {}
        self.offers: list[Offer] = []
        self.locations: dict[uuid.UUID, Location] = {}
        self.slots: list[Slot] = []
        self.promos: list[Promo] = []
        self.names: dict[str, uuid.UUID] = {}

    def _id(self, name: str) -> uuid.UUID:
        return self.names.setdefault(name, uuid.uuid5(uuid.NAMESPACE_URL, f"test:{name}"))

    def product(self, name: str, unit: str = "each", measure: int = 1) -> uuid.UUID:
        pid = self._id(f"product:{name}")
        self.products[pid] = ProductInfo(pid, unit, measure)
        return pid

    def store(
        self,
        name: str,
        *,
        fee: int = 4000,
        minimum: int = 0,
        pick: int = 0,
        first_slot: int = 60,
        slots: int = 3,
        spacing: int = 60,
        capacity: int = 5,
    ) -> uuid.UUID:
        lid = self._id(f"store:{name}")
        self.locations[lid] = Location(lid, self._id(f"merchant:{name}"), name, minimum, pick)
        for i in range(slots):
            start = NOW + timedelta(minutes=first_slot + i * spacing)
            self.slots.append(
                Slot(
                    self._id(f"slot:{name}:{i}"),
                    lid,
                    start,
                    start + timedelta(hours=1),
                    fee,
                    capacity,
                )
            )
        return lid

    def offer(self, store: uuid.UUID, product: uuid.UUID, price: int, stock: int | None = None):
        oid = self._id(f"offer:{store}:{product}")
        self.offers.append(Offer(oid, store, product, price, stock))
        return oid

    def promo(self, store: uuid.UUID, kind: str, **kw) -> uuid.UUID:
        pid = uuid.uuid4()
        kw.setdefault("product_ids", frozenset())
        self.promos.append(Promo(pid, store, kind, **kw))
        return pid

    def problem(self, lines: list[LineRequest], **kw) -> Problem:
        kw.setdefault("now", NOW)
        return Problem(
            lines=tuple(lines),
            products=dict(self.products),
            offers=tuple(self.offers),
            locations=dict(self.locations),
            slots=tuple(self.slots),
            promotions=tuple(self.promos),
            **kw,
        )


def line(
    line_id: str,
    *products: uuid.UUID,
    rule: Rule = Rule.FLEXIBLE,
    packs: int | None = 1,
    measure: int | None = None,
    unit: str | None = None,
    must_have: bool = False,
    ranks: tuple[int, ...] | None = None,
    caps: tuple[int | None, ...] | None = None,
):
    quantity = Quantity(measure=measure, unit=unit) if measure else Quantity(packs=packs)
    cands = tuple(
        Candidate(
            p, rank=(ranks[i] if ranks else 0), max_unit_price_minor=(caps[i] if caps else None)
        )
        for i, p in enumerate(products)
    )
    return LineRequest(line_id, rule, cands, quantity, must_have)


def oracle_cheapest(problem: Problem) -> int | None:
    """Minimum customer total over every store set (<= max_stores) and every assignment."""
    promos_at: dict[uuid.UUID, list[Promo]] = {}
    for p in problem.promotions:
        promos_at.setdefault(p.location_id, []).append(p)

    def choices(ln: LineRequest, store_set) -> list[tuple]:
        out = []
        for cand in ln.candidates:
            prod = problem.products[cand.product_id]
            units = units_for(ln, prod)
            if units is None:
                continue
            for o in problem.offers:
                if o.product_id != cand.product_id or o.location_id not in store_set:
                    continue
                if o.stock_quantity is not None and o.stock_quantity < units:
                    continue
                total, _, _ = price_line(
                    o, units, promos_at.get(o.location_id, []), problem.loyalty_programmes
                )
                if (
                    cand.max_unit_price_minor is not None
                    and total > cand.max_unit_price_minor * units
                ):
                    continue
                out.append((o, units, total, cand.rank if ln.rule is Rule.PREFERRED else 0))
        if ln.rule is Rule.PREFERRED and out:
            best = min(c[3] for c in out)
            out = [c for c in out if c[3] == best]
        return out

    def slot_fee(loc) -> int | None:
        earliest = problem.now + timedelta(minutes=problem.locations[loc].pick_minutes)
        fees = [
            s.fee_minor
            for s in problem.slots
            if s.location_id == loc
            and s.remaining > 0
            and s.starts_at >= earliest
            and (problem.deadline is None or s.ends_at <= problem.deadline)
        ]
        return min(fees) if fees else None

    best = None
    locs = list(problem.locations)
    for size in range(1, problem.max_stores + 1):
        for store_set in itertools.combinations(locs, size):
            base = {loc: slot_fee(loc) for loc in store_set}
            if any(v is None for v in base.values()):
                continue
            per_line = [choices(ln, store_set) for ln in problem.lines]
            if any(not c for c in per_line):
                continue
            for combo in itertools.product(*per_line):
                goods = dict.fromkeys(store_set, 0)
                stock: dict = {}
                ok = True
                for o, units, total, _ in combo:
                    goods[o.location_id] += total
                    key = (o.location_id, o.product_id)
                    stock[key] = stock.get(key, 0) + units
                    if o.stock_quantity is not None and stock[key] > o.stock_quantity:
                        ok = False
                if not ok or any(g == 0 for g in goods.values()):
                    continue
                if any(goods[s] < problem.locations[s].minimum_order_minor for s in store_set):
                    continue
                fees = 0
                for loc in store_set:
                    free = any(
                        p.kind == "delivery_threshold"
                        and p.location_id == loc
                        and goods[loc] >= p.min_spend_minor
                        for p in problem.promotions
                    )
                    fees += 0 if free else base[loc]
                total = sum(goods.values()) + fees + problem.service_fee_minor
                if best is None or total < best:
                    best = total
    return best

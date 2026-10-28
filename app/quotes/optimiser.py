"""Deterministic basket optimiser (blueprint §11; DECISIONS.md D-S03.1, D-S03.3).

Pure function of its inputs: no database, no clock, no randomness. Hard constraints
(product identity, quantity, preference rules, stock, merchant minimums, delivery
capacity and deadline, max two stores) are never traded for price. When no feasible
basket exists, the result names the blocking constraints instead of shrinking the list.

Prices are VAT-inclusive integer cents and are never taxed again (T13).
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from itertools import combinations

POLICY_VERSION = "balanced-v1"
BALANCED_SLACK = timedelta(minutes=30)


class Rule(StrEnum):
    LOCKED = "locked"  # only the listed equivalent set; unavailable means ask (T04)
    PREFERRED = "preferred"  # primary, then pre-approved fallbacks with conditions
    FLEXIBLE = "flexible"  # cheapest among the eligible candidates


class Strategy(StrEnum):
    CHEAPEST = "cheapest"
    FASTEST_COMPLETE = "fastest_complete"
    BALANCED = "balanced"


@dataclass(frozen=True)
class Candidate:
    product_id: uuid.UUID
    rank: int = 0
    max_unit_price_minor: int | None = None  # condition on a fallback


@dataclass(frozen=True)
class Quantity:
    """Either an exact number of sellable units, or an exact total measure (e.g. 2000 ml).

    A measure is met only by packs that add up to exactly that amount (T02, T14).
    """

    packs: int | None = None
    measure: int | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        if (self.packs is None) == (self.measure is None):
            raise ValueError("quantity needs exactly one of packs or measure")
        if (self.packs is not None and self.packs <= 0) or (
            self.measure is not None and (self.measure <= 0 or not self.unit)
        ):
            raise ValueError("quantity must be positive with a unit for measures")


@dataclass(frozen=True)
class LineRequest:
    line_id: str
    rule: Rule
    candidates: tuple[Candidate, ...]
    quantity: Quantity
    must_have: bool = False


@dataclass(frozen=True)
class ProductInfo:
    product_id: uuid.UUID
    unit: str
    total_measure: int


@dataclass(frozen=True)
class Offer:
    offer_version_id: uuid.UUID
    location_id: uuid.UUID
    product_id: uuid.UUID
    price_minor: int
    stock_quantity: int | None


@dataclass(frozen=True)
class Location:
    location_id: uuid.UUID
    merchant_id: uuid.UUID
    code: str
    minimum_order_minor: int = 0
    pick_minutes: int = 0


@dataclass(frozen=True)
class Slot:
    slot_id: uuid.UUID
    location_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    fee_minor: int
    remaining: int


@dataclass(frozen=True)
class Promo:
    promotion_id: uuid.UUID
    location_id: uuid.UUID
    kind: str
    product_ids: frozenset[uuid.UUID] = frozenset()
    min_quantity: int = 1
    min_spend_minor: int = 0
    benefit_minor: int = 0
    percent_bp: int = 0
    bundle_price_minor: int | None = None
    price_minor: int | None = None
    requires_loyalty_programme: str | None = None


@dataclass(frozen=True)
class Problem:
    lines: tuple[LineRequest, ...]
    products: dict[uuid.UUID, ProductInfo]
    offers: tuple[Offer, ...]
    locations: dict[uuid.UUID, Location]
    slots: tuple[Slot, ...]
    promotions: tuple[Promo, ...] = ()
    loyalty_programmes: frozenset[str] = frozenset()
    now: datetime | None = None
    deadline: datetime | None = None
    service_fee_minor: int = 0
    budget_minor: int | None = None
    allow_omit_optional: bool = False
    max_stores: int = 2
    node_budget: int = 200_000


@dataclass(frozen=True)
class LinePlan:
    line_id: str
    product_id: uuid.UUID
    offer_version_id: uuid.UUID
    units: int
    unit_price_minor: int
    discount_minor: int
    line_total_minor: int
    promotion_id: uuid.UUID | None


@dataclass(frozen=True)
class LegPlan:
    location_id: uuid.UUID
    merchant_id: uuid.UUID
    lines: tuple[LinePlan, ...]
    goods_minor: int
    delivery_fee_minor: int
    delivery_promotion_id: uuid.UUID | None
    slot_id: uuid.UUID
    window_start: datetime
    window_end: datetime


@dataclass(frozen=True)
class Option:
    strategy: Strategy
    legs: tuple[LegPlan, ...]
    goods_minor: int
    delivery_minor: int
    service_fee_minor: int
    total_minor: int
    completion: datetime
    proven_optimal: bool
    over_budget: bool
    policy_version: str = POLICY_VERSION

    @property
    def leg_count(self) -> int:
        return len(self.legs)


@dataclass(frozen=True)
class Blocking:
    kind: str
    detail: str
    line_id: str | None = None
    amount_minor: int | None = None


@dataclass
class Result:
    options: dict[Strategy, Option | None]
    blocking: list[Blocking] = field(default_factory=list)
    omitted_line_ids: tuple[str, ...] = ()
    requested_line_count: int = 0


# --- Pricing ---------------------------------------------------------------------------


def units_for(line: LineRequest, product: ProductInfo) -> int | None:
    """Sellable units of `product` that satisfy the line exactly, or None."""
    q = line.quantity
    if q.packs is not None:
        return q.packs
    if q.unit != product.unit or q.measure % product.total_measure:
        return None
    return q.measure // product.total_measure


def price_line(
    offer: Offer, units: int, promos: Iterable[Promo], loyalty: frozenset[str]
) -> tuple[int, int, uuid.UUID | None]:
    """(line total, discount, promotion id) using the single best item-level promotion."""
    base = offer.price_minor * units
    best = (base, None)
    for p in sorted(promos, key=lambda p: str(p.promotion_id)):
        if offer.product_id not in p.product_ids or units < p.min_quantity:
            continue
        if p.kind == "loyalty_price":
            if p.requires_loyalty_programme not in loyalty or p.price_minor is None:
                continue  # T12: an unearned loyalty price is never applied
            total = min(p.price_minor, offer.price_minor) * units
        elif p.kind == "fixed_line":
            total = base - min(p.benefit_minor, offer.price_minor) * units
        elif p.kind == "percent_line":
            total = base - (offer.price_minor * p.percent_bp // 10_000) * units
        elif p.kind == "multibuy" and p.bundle_price_minor is not None:
            bundles, rest = divmod(units, p.min_quantity)
            total = bundles * p.bundle_price_minor + rest * offer.price_minor
        else:
            continue  # unsupported promotions are ignored, never guessed
        if total < best[0]:
            best = (total, p.promotion_id)
    return best[0], base - best[0], best[1]


@dataclass(frozen=True)
class _Choice:
    location_id: uuid.UUID
    offer: Offer
    units: int
    total: int
    discount: int
    promotion_id: uuid.UUID | None
    rank: int


def _line_choices(problem: Problem) -> dict[str, list[_Choice]]:
    promos_at: dict[uuid.UUID, list[Promo]] = {}
    for p in problem.promotions:
        promos_at.setdefault(p.location_id, []).append(p)
    offers_by_product: dict[uuid.UUID, list[Offer]] = {}
    for o in problem.offers:
        offers_by_product.setdefault(o.product_id, []).append(o)
    choices: dict[str, list[_Choice]] = {}
    for line in problem.lines:
        out: list[_Choice] = []
        for cand in line.candidates:
            product = problem.products.get(cand.product_id)
            if product is None:
                continue
            units = units_for(line, product)
            if units is None:
                continue
            for offer in offers_by_product.get(cand.product_id, []):
                if offer.location_id not in problem.locations:
                    continue
                if offer.stock_quantity is not None and offer.stock_quantity < units:
                    continue
                total, discount, promo = price_line(
                    offer, units, promos_at.get(offer.location_id, []), problem.loyalty_programmes
                )
                if cand.max_unit_price_minor is not None and total > (
                    cand.max_unit_price_minor * units
                ):
                    continue  # fallback condition not met
                rank = cand.rank if line.rule is Rule.PREFERRED else 0
                out.append(_Choice(offer.location_id, offer, units, total, discount, promo, rank))
        out.sort(key=lambda c: (c.total, str(c.location_id), str(c.offer.product_id)))
        choices[line.line_id] = out
    return choices


def _restrict_to_set(
    line: LineRequest, choices: list[_Choice], store_set: frozenset[uuid.UUID]
) -> list[_Choice]:
    in_set = [c for c in choices if c.location_id in store_set]
    if line.rule is Rule.PREFERRED and in_set:
        best_rank = min(c.rank for c in in_set)
        in_set = [c for c in in_set if c.rank == best_rank]
    return in_set


# --- Assignment within one store set ---------------------------------------------------


@dataclass
class _Assignment:
    picks: dict[str, _Choice]
    goods: dict[uuid.UUID, int]
    fees: dict[uuid.UUID, tuple[int, uuid.UUID | None]]
    total: int


def _fee(
    loc: uuid.UUID, goods: int, base_fee: int, thresholds: dict[uuid.UUID, list[Promo]]
) -> tuple[int, uuid.UUID | None]:
    for p in sorted(thresholds.get(loc, []), key=lambda p: str(p.promotion_id)):
        if goods >= p.min_spend_minor:  # evaluated on post-discount goods (D-S03.3)
            return 0, p.promotion_id
    return base_fee, None


class _Budget:
    def __init__(self, nodes: int) -> None:
        self.remaining = nodes
        self.exhausted = False

    def spend(self) -> bool:
        self.remaining -= 1
        if self.remaining < 0:
            self.exhausted = True
        return not self.exhausted


def _solve_set(
    lines: list[LineRequest],
    per_line: dict[str, list[_Choice]],
    store_set: frozenset[uuid.UUID],
    base_fees: dict[uuid.UUID, int],
    problem: Problem,
    budget: _Budget,
    failures: set[str],
) -> _Assignment | None:
    thresholds: dict[uuid.UUID, list[Promo]] = {}
    for p in problem.promotions:
        if p.kind == "delivery_threshold" and p.location_id in store_set:
            thresholds.setdefault(p.location_id, []).append(p)
    ordered = sorted(lines, key=lambda ln: (len(per_line[ln.line_id]), ln.line_id))
    suffix_min = [0] * (len(ordered) + 1)
    for i in range(len(ordered) - 1, -1, -1):
        suffix_min[i] = suffix_min[i + 1] + per_line[ordered[i].line_id][0].total
    always_fee = sum(fee for loc, fee in base_fees.items() if loc not in thresholds)

    best: _Assignment | None = None
    picks: dict[str, _Choice] = {}
    goods = dict.fromkeys(store_set, 0)
    stock_used: dict[tuple[uuid.UUID, uuid.UUID], int] = {}

    def leaf(cost: int) -> None:
        nonlocal best
        if any(goods[loc] == 0 for loc in store_set):
            failures.add("store_unused")  # covered by the smaller store set
            return
        for loc in store_set:
            if goods[loc] < problem.locations[loc].minimum_order_minor:
                failures.add("merchant_minimum")
                return
        fees = {loc: _fee(loc, goods[loc], base_fees[loc], thresholds) for loc in store_set}
        total = cost + sum(f for f, _ in fees.values())
        if best is None or total < best.total:
            best = _Assignment(dict(picks), dict(goods), fees, total)

    def search(i: int, cost: int) -> None:
        if not budget.spend():
            return
        if best is not None and cost + suffix_min[i] + always_fee >= best.total:
            return
        if i == len(ordered):
            leaf(cost)
            return
        line = ordered[i]
        for choice in per_line[line.line_id]:
            key = (choice.location_id, choice.offer.product_id)
            stock = choice.offer.stock_quantity
            if stock is not None and stock_used.get(key, 0) + choice.units > stock:
                failures.add("stock")
                continue
            picks[line.line_id] = choice
            goods[choice.location_id] += choice.total
            stock_used[key] = stock_used.get(key, 0) + choice.units
            search(i + 1, cost + choice.total)
            stock_used[key] -= choice.units
            goods[choice.location_id] -= choice.total
            del picks[line.line_id]

    search(0, 0)
    return best


# --- Slots and strategies --------------------------------------------------------------


def _feasible_slots(problem: Problem, loc: uuid.UUID, bound: datetime | None) -> list[Slot]:
    location = problem.locations[loc]
    earliest = (
        None if problem.now is None else problem.now + timedelta(minutes=location.pick_minutes)
    )
    out = [
        s
        for s in problem.slots
        if s.location_id == loc
        and s.remaining > 0
        and (earliest is None or s.starts_at >= earliest)
        and (bound is None or s.ends_at <= bound)
    ]
    return sorted(out, key=lambda s: (s.ends_at, s.fee_minor, str(s.slot_id)))


def _pick_slot(slots: list[Slot], strategy: Strategy) -> Slot:
    if strategy is Strategy.FASTEST_COMPLETE:
        return slots[0]
    return min(slots, key=lambda s: (s.fee_minor, s.ends_at, str(s.slot_id)))


def _build_option(
    strategy: Strategy,
    problem: Problem,
    assignment: _Assignment,
    slots: dict[uuid.UUID, Slot],
    proven: bool,
) -> Option:
    legs = []
    for loc in sorted(slots, key=lambda x: problem.locations[x].code):
        lines = tuple(
            LinePlan(
                line_id=line_id,
                product_id=c.offer.product_id,
                offer_version_id=c.offer.offer_version_id,
                units=c.units,
                unit_price_minor=c.offer.price_minor,
                discount_minor=c.discount,
                line_total_minor=c.total,
                promotion_id=c.promotion_id,
            )
            for line_id, c in sorted(assignment.picks.items())
            if c.location_id == loc
        )
        fee, fee_promo = assignment.fees[loc]
        legs.append(
            LegPlan(
                location_id=loc,
                merchant_id=problem.locations[loc].merchant_id,
                lines=lines,
                goods_minor=assignment.goods[loc],
                delivery_fee_minor=fee,
                delivery_promotion_id=fee_promo,
                slot_id=slots[loc].slot_id,
                window_start=slots[loc].starts_at,
                window_end=slots[loc].ends_at,
            )
        )
    goods = sum(leg.goods_minor for leg in legs)
    delivery = sum(leg.delivery_fee_minor for leg in legs)
    total = goods + delivery + problem.service_fee_minor
    return Option(
        strategy=strategy,
        legs=tuple(legs),
        goods_minor=goods,
        delivery_minor=delivery,
        service_fee_minor=problem.service_fee_minor,
        total_minor=total,
        completion=max(leg.window_end for leg in legs),
        proven_optimal=proven,
        over_budget=problem.budget_minor is not None and total > problem.budget_minor,
    )


def _tie_key(option: Option) -> tuple:
    return (
        option.total_minor,
        option.leg_count,
        option.completion,
        tuple(str(ln.offer_version_id) for leg in option.legs for ln in leg.lines),
    )


def optimise(problem: Problem) -> Result:
    result = Result(options=dict.fromkeys(Strategy), requested_line_count=len(problem.lines))
    choices = _line_choices(problem)

    lines: list[LineRequest] = []
    omitted: list[str] = []
    for line in problem.lines:
        if choices[line.line_id]:
            lines.append(line)
        elif problem.allow_omit_optional and not line.must_have:
            omitted.append(line.line_id)  # unavailable everywhere; disclosed, never chosen
        else:
            reason = "locked_unavailable" if line.rule is Rule.LOCKED else "unavailable"
            result.blocking.append(
                Blocking(
                    reason,
                    "no participating store can supply this item as specified",
                    line_id=line.line_id,
                )
            )
    result.omitted_line_ids = tuple(omitted)
    if result.blocking or not lines:
        if not lines and not result.blocking:
            result.blocking.append(Blocking("empty_basket", "no suppliable items remain"))
        return result

    locs = sorted(
        {c.location_id for ln in lines for c in choices[ln.line_id]},
        key=lambda loc: problem.locations[loc].code,
    )
    store_sets = [frozenset([loc]) for loc in locs]
    for size in range(2, problem.max_stores + 1):
        store_sets += [frozenset(c) for c in combinations(locs, size)]

    failures: set[str] = set()

    def evaluate(strategy: Strategy, bound: datetime | None) -> list[Option]:
        found: list[tuple[_Assignment, dict[uuid.UUID, Slot]]] = []
        exhausted = False
        for store_set in store_sets:
            per_line = {
                ln.line_id: _restrict_to_set(ln, choices[ln.line_id], store_set) for ln in lines
            }
            if any(not v for v in per_line.values()):
                failures.add("coverage")
                continue
            slots = {}
            for loc in store_set:
                feasible = _feasible_slots(problem, loc, bound)
                if not feasible:
                    failures.add("delivery_window")
                    break
                slots[loc] = _pick_slot(feasible, strategy)
            if len(slots) != len(store_set):
                continue
            fees = {loc: slot.fee_minor for loc, slot in slots.items()}
            budget = _Budget(problem.node_budget)
            assignment = _solve_set(lines, per_line, store_set, fees, problem, budget, failures)
            exhausted = exhausted or budget.exhausted
            if assignment is not None:
                found.append((assignment, slots))
        # T15: if any search ran out of budget, no option of this strategy is a proven optimum.
        return [_build_option(strategy, problem, a, s, not exhausted) for a, s in found]

    cheapest = evaluate(Strategy.CHEAPEST, problem.deadline)
    if cheapest:
        result.options[Strategy.CHEAPEST] = min(cheapest, key=_tie_key)
    fastest = evaluate(Strategy.FASTEST_COMPLETE, problem.deadline)
    if fastest:
        result.options[Strategy.FASTEST_COMPLETE] = min(
            fastest, key=lambda o: (o.completion, *_tie_key(o))
        )
        t_fastest = result.options[Strategy.FASTEST_COMPLETE].completion
        bound = t_fastest + BALANCED_SLACK
        if problem.deadline is not None:
            bound = min(bound, problem.deadline)
        balanced = evaluate(Strategy.BALANCED, bound)
        if balanced:
            result.options[Strategy.BALANCED] = min(balanced, key=_tie_key)

    if not any(result.options.values()):
        explanations = {
            "coverage": f"the list needs more than {problem.max_stores} stores",
            "merchant_minimum": "a store's minimum order is not reached",
            "delivery_window": "no delivery window meets the timing and capacity requirements",
            "stock": "available stock does not cover the requested quantities",
        }
        for kind in sorted(failures - {"store_unused"}):
            result.blocking.append(Blocking(kind, explanations[kind]))
        if not result.blocking:
            result.blocking.append(Blocking("infeasible", "no feasible basket found"))
    cheapest_option = result.options[Strategy.CHEAPEST]
    if cheapest_option is not None and cheapest_option.over_budget:
        result.blocking.append(
            Blocking(
                "budget",
                "the full list costs more than the budget; choose items to postpone",
                amount_minor=cheapest_option.total_minor - problem.budget_minor,
            )
        )
    return result

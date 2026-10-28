"""Optimiser: T04, T11-T17, preferences, omissions, budget, and an oracle property test."""

from datetime import timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from app.quotes.optimiser import Offer, Rule, Strategy, optimise, price_line
from tests.optimiser_support import NOW, World, line, oracle_cheapest

C, F, B = Strategy.CHEAPEST, Strategy.FASTEST_COMPLETE, Strategy.BALANCED


def _codes(world: World, option) -> list[str]:
    return [world.locations[leg.location_id].code for leg in option.legs]


def test_single_store_basket_and_totals_are_vat_inclusive_t13():
    w = World()
    a = w.store("a", fee=4000)
    milk, rice = w.product("milk"), w.product("rice")
    w.offer(a, milk, 1899)
    w.offer(a, rice, 4299)
    r = optimise(w.problem([line("l1", milk), line("l2", rice, packs=2)], service_fee_minor=2000))
    opt = r.options[C]
    # Goods are summed as quoted; VAT is already included and never added again.
    assert opt.goods_minor == 1899 + 2 * 4299
    assert opt.total_minor == opt.goods_minor + 4000 + 2000
    assert opt.proven_optimal and not r.blocking


def test_t11_delivery_threshold_changes_optimal_split():
    """Without the threshold, splitting is cheapest; with free delivery at R800 at store A,
    consolidating at A wins even though B's item price is lower."""
    w = World()
    a, b = w.store("a", fee=4500), w.store("b", fee=4000)
    big, small = w.product("big"), w.product("small")
    w.offer(a, big, 78000)
    w.offer(a, small, 3000)
    w.offer(b, small, 2000)
    w.offer(b, big, 90000)
    lines = [line("big", big), line("small", small)]
    no_threshold = optimise(w.problem(lines)).options[C]
    assert no_threshold.total_minor == 78000 + 3000 + 4500  # single store A: 85500 < split 88500
    w.promo(a, "delivery_threshold", min_spend_minor=80000)
    with_threshold = optimise(w.problem(lines)).options[C]
    assert _codes(w, with_threshold) == ["a"] and with_threshold.delivery_minor == 0
    assert with_threshold.total_minor == 81000
    assert with_threshold.total_minor == oracle_cheapest(w.problem(lines))

    # Now make the split clearly better on price: B's small item is much cheaper.
    w2 = World()
    a, b = w2.store("a", fee=4500), w2.store("b", fee=1000)
    big, small = w2.product("big"), w2.product("small")
    w2.offer(a, big, 78000)
    w2.offer(a, small, 5000)
    w2.offer(b, small, 2000)
    split = optimise(w2.problem([line("big", big), line("small", small)])).options[C]
    assert _codes(w2, split) == ["a", "b"]
    assert split.total_minor == 78000 + 4500 + 2000 + 1000
    w2.promo(a, "delivery_threshold", min_spend_minor=80000)
    consolidated = optimise(w2.problem([line("big", big), line("small", small)])).options[C]
    assert _codes(w2, consolidated) == ["a"] and consolidated.total_minor == 83000
    assert consolidated.total_minor == oracle_cheapest(
        w2.problem([line("big", big), line("small", small)])
    )


def test_t12_loyalty_price_requires_verified_membership():
    w = World()
    a = w.store("a")
    oil = w.product("oil")
    w.offer(a, oil, 6199)
    w.promo(
        a,
        "loyalty_price",
        product_ids=frozenset([oil]),
        price_minor=4999,
        requires_loyalty_programme="rewards",
    )
    without = optimise(w.problem([line("oil", oil)])).options[C]
    member = optimise(w.problem([line("oil", oil)], loyalty_programmes=frozenset({"rewards"})))
    assert without.goods_minor == 6199 and without.legs[0].lines[0].promotion_id is None
    assert member.options[C].goods_minor == 4999


def test_t14_lower_unit_price_never_exceeds_requested_quantity():
    """2 litres requested: two 1 L units, never the cheaper-per-litre 6 x 1 L pack."""
    w = World()
    a = w.store("a")
    one = w.product("milk-1l", unit="ml", measure=1000)
    six = w.product("milk-6x1l", unit="ml", measure=6000)
    w.offer(a, one, 1899)
    w.offer(a, six, 9999)
    r = optimise(w.problem([line("milk", one, six, measure=2000, unit="ml")]))
    plan = r.options[C].legs[0].lines[0]
    assert plan.product_id == one and plan.units == 2 and plan.line_total_minor == 3798


def test_t02_pack_count_is_not_a_measure():
    """'two 2 L bottles' (packs=2) and '2 litres' (measure=2000 ml) are different requests."""
    w = World()
    a = w.store("a")
    two_l = w.product("oil-2l", unit="ml", measure=2000)
    w.offer(a, two_l, 6000)
    packs = optimise(w.problem([line("x", two_l, packs=2)])).options[C].legs[0].lines[0]
    measure = optimise(w.problem([line("x", two_l, measure=2000, unit="ml")]))
    assert packs.units == 2
    assert measure.options[C].legs[0].lines[0].units == 1


def test_t04_locked_item_unavailable_blocks_without_substitute():
    w = World()
    a = w.store("a")
    locked, other = w.product("locked"), w.product("other")
    w.offer(a, other, 100)  # a cheaper alternative exists but is not in the locked set
    r = optimise(w.problem([line("l", locked, rule=Rule.LOCKED)]))
    assert all(v is None for v in r.options.values())
    assert [(b.kind, b.line_id) for b in r.blocking] == [("locked_unavailable", "l")]


def test_preferred_uses_primary_then_conditional_fallback():
    w = World()
    a, b = w.store("a"), w.store("b")
    primary, fallback = w.product("primary"), w.product("fallback")
    w.offer(a, primary, 3000)
    w.offer(b, fallback, 1000)
    pref = line("l", primary, fallback, rule=Rule.PREFERRED, ranks=(0, 1), caps=(None, 1500))
    r = optimise(w.problem([pref]))
    # Store set {a,b} must use the primary; fallback only where the primary is not offered.
    assert r.options[C].legs[0].lines[0].product_id == fallback  # b alone: fallback within cap
    capped = line("l", primary, fallback, rule=Rule.PREFERRED, ranks=(0, 1), caps=(None, 900))
    r2 = optimise(w.problem([capped]))
    assert r2.options[C].legs[0].lines[0].product_id == primary  # fallback cap not met


def test_t15_solver_budget_exhausted_returns_honest_feasible_incumbent():
    w = World()
    stores = [w.store(s) for s in "abcd"]
    products = [w.product(f"p{i}") for i in range(10)]
    for i, p in enumerate(products):
        for j, s in enumerate(stores):
            w.offer(s, p, 1000 + 37 * ((i * 7 + j * 3) % 11))
    lines = [line(f"l{i}", p) for i, p in enumerate(products)]
    exact = optimise(w.problem(lines)).options[C]
    limited = optimise(w.problem(lines, node_budget=12)).options[C]
    assert exact.proven_optimal
    assert limited is not None and not limited.proven_optimal
    assert limited.total_minor >= exact.total_minor
    assert {ln.line_id for leg in limited.legs for ln in leg.lines} == {f"l{i}" for i in range(10)}


def test_t16_cheapest_basket_that_misses_deadline_is_excluded():
    w = World()
    slow = w.store("slow", fee=1000, first_slot=300)
    fast = w.store("fast", fee=5000, first_slot=30)
    item = w.product("item")
    w.offer(slow, item, 1000)
    w.offer(fast, item, 1500)
    no_deadline = optimise(w.problem([line("l", item)])).options[C]
    assert _codes(w, no_deadline) == ["slow"]
    r = optimise(w.problem([line("l", item)], deadline=NOW + timedelta(hours=2)))
    assert _codes(w, r.options[C]) == ["fast"]
    assert all(o.completion <= NOW + timedelta(hours=2) for o in r.options.values() if o)


def test_t17_fastest_complete_uses_final_leg():
    """A split with one very fast leg and one slow leg completes at the slow leg."""
    w = World()
    quick = w.store("quick", first_slot=15, fee=1000)
    slow = w.store("slow", first_slot=240, fee=1000)
    steady = w.store("steady", first_slot=90, fee=9000)
    x, y = w.product("x"), w.product("y")
    w.offer(quick, x, 100)
    w.offer(slow, y, 100)
    w.offer(steady, x, 400)
    w.offer(steady, y, 400)
    r = optimise(w.problem([line("x", x), line("y", y)]))
    assert _codes(w, r.options[C]) == ["quick", "slow"]
    fastest = r.options[F]
    assert _codes(w, fastest) == ["steady"]
    assert fastest.completion == NOW + timedelta(minutes=150)


def test_balanced_is_cheapest_within_thirty_minutes_of_fastest():
    w = World()
    fastest = w.store("fastest", first_slot=60, fee=6000)
    near = w.store("near", first_slot=85, fee=3000)
    far = w.store("far", first_slot=200, fee=500)
    item = w.product("item")
    for s in (fastest, near, far):
        w.offer(s, item, 1000)
    r = optimise(w.problem([line("l", item)]))
    assert _codes(w, r.options[F]) == ["fastest"]
    assert _codes(w, r.options[B]) == ["near"]  # within +30 min, cheaper
    assert _codes(w, r.options[C]) == ["far"]


def test_merchant_minimum_and_max_two_stores_are_named():
    w = World()
    stores = [w.store(s, minimum=0) for s in "abc"]
    items = [w.product(f"i{k}") for k in range(3)]
    for s, i in zip(stores, items, strict=True):
        w.offer(s, i, 1000)  # each item only at its own store: needs three stores
    r = optimise(w.problem([line(f"l{k}", i) for k, i in enumerate(items)]))
    assert r.options[C] is None
    assert "coverage" in {b.kind for b in r.blocking}

    w2 = World()
    a = w2.store("a", minimum=5000)
    item = w2.product("item")
    w2.offer(a, item, 1000)
    r2 = optimise(w2.problem([line("l", item)]))
    assert {b.kind for b in r2.blocking} == {"merchant_minimum"}


def test_stock_is_shared_across_lines_and_never_exceeded():
    w = World()
    a, b = w.store("a", fee=0), w.store("b", fee=0)
    item = w.product("item")
    w.offer(a, item, 1000, stock=2)
    w.offer(b, item, 1500, stock=5)
    r = optimise(w.problem([line("l1", item, packs=2), line("l2", item, packs=2)]))
    used = {}
    for leg in r.options[C].legs:
        for ln in leg.lines:
            used[leg.location_id] = used.get(leg.location_id, 0) + ln.units
    assert used[a] <= 2 and r.options[C].total_minor == 2000 + 3000


def test_budget_shortfall_is_reported_not_shrunk():
    w = World()
    a = w.store("a", fee=4000)
    item = w.product("item")
    w.offer(a, item, 50000)
    r = optimise(w.problem([line("l", item, packs=4)], budget_minor=200000))
    opt = r.options[C]
    assert opt.over_budget and opt.legs[0].lines[0].units == 4  # quantity never reduced
    budget = next(b for b in r.blocking if b.kind == "budget")
    assert budget.amount_minor == 204000 - 200000


def test_optional_unavailable_line_omitted_only_when_permitted_and_disclosed():
    w = World()
    a = w.store("a")
    have, missing = w.product("have"), w.product("missing")
    w.offer(a, have, 1000)
    lines = [line("have", have), line("missing", missing)]
    strict = optimise(w.problem(lines))
    assert strict.options[C] is None
    partial = optimise(w.problem(lines, allow_omit_optional=True))
    assert partial.omitted_line_ids == ("missing",) and partial.options[C].goods_minor == 1000
    must = optimise(
        w.problem(
            [line("have", have), line("missing", missing, must_have=True)], allow_omit_optional=True
        )
    )
    assert must.options[C] is None
    assert [b.line_id for b in must.blocking] == ["missing"]


def test_promotions_pricing_rules():
    w = World()
    a = w.store("a")
    beans = w.product("beans")
    o = Offer(w._id("o"), a, beans, 1599, None)
    multibuy = w.promo(
        a, "multibuy", product_ids=frozenset([beans]), min_quantity=3, bundle_price_minor=4200
    )
    percent = w.promo(a, "percent_line", product_ids=frozenset([beans]), percent_bp=1000)
    promos = [p for p in w.promos]
    assert price_line(o, 3, promos, frozenset()) == (4200, 597, multibuy)  # best single promo
    assert price_line(o, 2, promos, frozenset()) == (2 * (1599 - 159), 318, percent)
    # 4 units: 10% off each (R57.60) beats one bundle plus one single (R57.99).
    assert price_line(o, 4, promos, frozenset()) == (4 * (1599 - 159), 636, percent)


def test_results_are_deterministic():
    w = World()
    a, b = w.store("a"), w.store("b")
    item = w.product("item")
    w.offer(a, item, 1000)
    w.offer(b, item, 1000)  # exact tie: stable ordering decides
    first = optimise(w.problem([line("l", item)]))
    second = optimise(w.problem([line("l", item)]))
    assert first.options == second.options


# --- Oracle property test ------------------------------------------------------------


@st.composite
def worlds(draw):
    w = World()
    n_stores = draw(st.integers(1, 4))
    stores = [
        w.store(
            f"s{i}",
            fee=draw(st.sampled_from([0, 1500, 4000])),
            minimum=draw(st.sampled_from([0, 0, 3000])),
            first_slot=draw(st.sampled_from([30, 60, 120])),
        )
        for i in range(n_stores)
    ]
    products = [
        w.product(f"p{i}", unit="g", measure=draw(st.sampled_from([500, 1000])))
        for i in range(draw(st.integers(1, 4)))
    ]
    for s in stores:
        for p in products:
            if draw(st.booleans()):
                w.offer(
                    s,
                    p,
                    draw(st.integers(100, 5000)),
                    stock=draw(st.one_of(st.none(), st.integers(0, 4))),
                )
        if draw(st.booleans()):
            w.promo(s, "delivery_threshold", min_spend_minor=draw(st.integers(1000, 8000)))
        if products and draw(st.booleans()):
            w.promo(
                s,
                "multibuy",
                product_ids=frozenset([draw(st.sampled_from(products))]),
                min_quantity=2,
                bundle_price_minor=draw(st.integers(100, 6000)),
            )
    lines = []
    for i in range(draw(st.integers(1, 4))):
        cands = draw(st.lists(st.sampled_from(products), min_size=1, max_size=3, unique=True))
        rule = draw(st.sampled_from([Rule.FLEXIBLE, Rule.PREFERRED, Rule.LOCKED]))
        if draw(st.booleans()):
            lines.append(
                line(
                    f"l{i}",
                    *cands,
                    rule=rule,
                    packs=draw(st.integers(1, 3)),
                    ranks=tuple(range(len(cands))),
                )
            )
        else:
            lines.append(
                line(
                    f"l{i}",
                    *cands,
                    rule=rule,
                    measure=draw(st.sampled_from([1000, 2000])),
                    unit="g",
                    ranks=tuple(range(len(cands))),
                )
            )
    return w, lines


@settings(deadline=None)
@given(worlds())
def test_property_cheapest_matches_brute_force_oracle(data):
    w, lines = data
    problem = w.problem(lines, service_fee_minor=2000)
    result = optimise(problem)
    expected = oracle_cheapest(problem)
    got = result.options[C]
    if expected is None:
        assert got is None and result.blocking
    else:
        assert got is not None and got.proven_optimal
        assert got.total_minor == expected
        # Every option honours hard constraints: all lines present, at most two stores.
        for opt in filter(None, result.options.values()):
            assert opt.leg_count <= 2
            assert {ln.line_id for leg in opt.legs for ln in leg.lines} == {
                ln.line_id for ln in lines
            }


# --- Against the seeded catalogue ----------------------------------------------------


def test_seeded_catalogue_produces_three_options(db, catalogue):
    from app.quotes.inputs import build_problem
    from app.quotes.optimiser import Candidate, LineRequest, Quantity
    from tests.conftest import T0

    def req(code, rule=Rule.FLEXIBLE, **q):
        return LineRequest(
            code, rule, (Candidate(catalogue[f"product:{code}"]),), Quantity(**(q or {"packs": 1}))
        )

    lines = [req("milk-1l", packs=2), req("maize-5kg"), req("tea-100"), req("beans-410g", packs=3)]
    problem = build_problem(db, lines=lines, zone="zone-a", now=T0)
    result = optimise(problem)
    assert not result.blocking
    cheapest, fastest, balanced = (result.options[s] for s in (C, F, B))
    assert cheapest.total_minor <= balanced.total_minor
    assert fastest.completion <= balanced.completion <= fastest.completion + timedelta(minutes=30)
    for opt in (cheapest, fastest, balanced):
        assert opt.leg_count <= 2 and opt.service_fee_minor == 2000

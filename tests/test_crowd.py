"""The crowd draw: random each run, but always has attackers, model citizens and broke
shoppers, and every persona lives in a zone the market serves."""

import random

from app.simulators.market import MARKET_ZONES
from scripts.crowd.personas import COLLOQUIAL, draw_crowd


def test_crowd_has_required_archetypes_and_valid_zones():
    for seed in range(50):
        crowd = draw_crowd(60, random.Random(seed))
        kinds = {p.archetype.key for p in crowd}
        assert len(crowd) == 60
        assert {"malicious", "careful", "broke"} <= kinds
        assert all(p.zone in MARKET_ZONES for p in crowd)
        assert len({p.name for p in crowd}) == 60


def test_two_draws_differ():
    a = draw_crowd(60, random.Random(1))
    b = draw_crowd(60, random.Random(2))
    assert [p.archetype.key for p in a] != [p.archetype.key for p in b]


def test_colloquial_targets_exist_in_catalogue_or_are_declared_gaps():
    """Every everyday word maps to something the large market sells, or is a declared gap."""
    from app.simulators.bigmarket import FURNITURE, TYPES

    names = " ".join(
        [f"{t[1]} {' '.join(t[6])}" for t in TYPES]
        + [f"{f[1]} {' '.join(f[3])}" for f in FURNITURE]
    ).lower()
    for word, target in COLLOQUIAL.items():
        assert target is None or target.lower() in names, word


def test_large_market_ranges_match_the_brief():
    from app.simulators.bigmarket import CHAINS, generate_universe, ranges

    universe = generate_universe()
    assert len(universe) > 60_000
    assert len({p.code for p in universe}) == len(universe)
    sizes = {code: len(products) for code, products in ranges(universe).items()}
    assert sizes["ubuntu"] == 50_000 and sizes["zest"] == 20_000 and sizes["fairbasket"] == 18_000
    for chain in CHAINS:  # nearest-branch rule: one branch per zone per chain
        zones = [z for b in chain.branches for z in b.zones]
        assert len(zones) == len(set(zones)), chain.code


def test_scam_store_undercuts_the_market_on_its_bait_lines():
    from app.simulators.bigmarket import CHAINS, chain_price, generate_universe, ranges

    universe = generate_universe()
    by = ranges(universe)
    chains = {c.code: c for c in CHAINS}
    scam = chains["bargainbox"]
    fair = chains["fairbasket"]
    carried = {p.code for p in by["fairbasket"]}
    cheaper = [
        chain_price(scam, scam.branches[0], p) < chain_price(fair, fair.branches[0], p)
        for p in by["bargainbox"]
        if p.code in carried
    ]
    assert cheaper and sum(cheaper) / len(cheaper) > 0.9

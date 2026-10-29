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
    from app.simulators.market import MARKET_PRODUCTS

    names = " ".join(f"{p.brand} {p.name} {p.variant}".lower() for p in MARKET_PRODUCTS)
    for word, target in COLLOQUIAL.items():
        assert target is None or target.lower() in names, word

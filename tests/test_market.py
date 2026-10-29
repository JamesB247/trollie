"""The crowd-simulation market: fictional multi-branch chains with nearest-branch service."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.merchants.models import MerchantLocation
from app.quotes.optimiser import Strategy
from app.simulators.market import CHAINS, MARKET_PRODUCTS, MARKET_ZONES, listing, seed_market
from tests.conftest import T0
from tests.flows import estimate, new_customer, shopping_list


@pytest.fixture(scope="module")
def market(engine):
    with Session(engine) as s, s.begin():
        return seed_market(s, now=T0)


def test_each_chain_serves_a_zone_from_at_most_one_branch():
    for chain in CHAINS:
        seen: dict[str, str] = {}
        for branch in chain.branches:
            for zone in branch.zones:
                assert zone in MARKET_ZONES
                assert zone not in seen, f"{chain.code}: {zone} served by {seen.get(zone)}"
                seen[zone] = branch.code


def test_every_zone_has_a_grocer_and_a_hardware_store():
    grocers = {z for c in CHAINS if "dairy" in c.categories for b in c.branches for z in b.zones}
    hardware = {
        z for c in CHAINS if "building" in c.categories for b in c.branches for z in b.zones
    }
    assert grocers == set(MARKET_ZONES)
    assert hardware == set(MARKET_ZONES)


def test_names_are_labelled_fictional_and_prices_are_shelf_style():
    assert all(c.name.endswith("(Fictional)") for c in CHAINS)
    for chain in CHAINS:
        for branch in chain.branches:
            for p in MARKET_PRODUCTS:
                listed = listing(chain, branch, p)
                if listed:
                    assert listed[0] % 100 == 99 and listed[1] >= 0


def test_seed_is_idempotent(engine, market):
    with Session(engine) as s, s.begin():
        before = s.scalar(select(func.count()).select_from(MerchantLocation))
        assert seed_market(s, now=T0) == market
        assert s.scalar(select(func.count()).select_from(MerchantLocation)) == before


def test_soweto_household_gets_a_basket_from_its_nearest_branches(db, market, clock):
    who = new_customer(db, zone="gp-soweto")
    sid = shopping_list(
        db,
        market,
        who,
        [
            ("mk-maize-10kg", {}),
            ("mk-oil-2l", {}),
            ("mk-bread-brown", {"packs": 2}),
            ("mk-cement-50kg", {"packs": 2}),
        ],
    )
    quote = estimate(db, who, sid, clock, Strategy.CHEAPEST)
    soweto_branches = {
        market[f"location:{b.code}"] for c in CHAINS for b in c.branches if "gp-soweto" in b.zones
    }
    legs = quote.snapshot["legs"]
    assert {str(x) for x in soweto_branches} >= {leg["location_id"] for leg in legs}
    assert len(legs) == 2  # groceries and cement cannot come from one chain

# ruff: noqa: E501 - tabular fixture data reads better unwrapped
"""Synthetic South African market for crowd simulations. SIMULATED — NOT REAL MONEY.

Six fictional chains with branches in four provinces. Every chain, branch and brand here is
invented. The chains are *archetypes* of how real South African retail works, not copies of
any retailer: no real names, logos, product listings or prices were taken from any site.
Base prices are rounded, hand-set illustrations of typical shelf price levels; each chain
applies its own category price index, and franchise branches set their own prices.

Nearest-branch rule: a chain serves a delivery zone from at most one branch, the way an
on-demand grocery app assigns the closest store. A customer therefore sees one branch per
chain, and the optimiser can still combine two different chains.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.delivery.models import DeliverySlot
from app.merchants.models import Merchant, MerchantCapability, MerchantLocation, MerchantState
from app.offers.models import OfferVersion, Promotion, PromotionKind, StockConfidence, TaxCode
from app.products.models import MatchLevel, Product, ProductMapping, Unit
from app.seed import COURIER, _ensure, gtin13, sid

Z, S = TaxCode.ZERO_RATED, TaxCode.STANDARD
G, ML, EA = Unit.G, Unit.ML, Unit.EACH

# Delivery zones, grouped by region. A zone stands for a cluster of suburbs.
REGIONS: dict[str, tuple[str, ...]] = {
    "Gauteng": ("gp-sandton", "gp-soweto", "gp-pretoria-east", "gp-midrand", "gp-tembisa"),
    "Western Cape": ("wc-city-bowl", "wc-khayelitsha", "wc-bellville"),
    "KwaZulu-Natal": ("kzn-umhlanga", "kzn-umlazi"),
    "Eastern Cape": ("ec-gqeberha",),
}
MARKET_ZONES = tuple(z for zones in REGIONS.values() for z in zones)


@dataclass(frozen=True)
class MP:
    """Market product: code, brand, name, variant, measure, unit, pack, category, tax,
    base shelf price in cents."""

    code: str
    brand: str
    name: str
    variant: str
    measure: int
    unit: Unit
    pack: int
    category: str
    tax: TaxCode
    base: int


# fmt: off
MARKET_PRODUCTS = [
    # Staples
    MP("mk-maize-2.5kg", "Highveld Mills", "Super maize meal", "", 2500, G, 1, "staples", Z, 4499),
    MP("mk-maize-5kg", "Highveld Mills", "Super maize meal", "", 5000, G, 1, "staples", Z, 7999),
    MP("mk-maize-10kg", "Highveld Mills", "Super maize meal", "", 10000, G, 1, "staples", Z, 13999),
    MP("mk-rice-2kg", "Karoo Kitchen", "Long grain rice", "", 2000, G, 1, "staples", Z, 4499),
    MP("mk-rice-5kg", "Karoo Kitchen", "Long grain rice", "", 5000, G, 1, "staples", Z, 10499),
    MP("mk-samp-2kg", "Highveld Mills", "Samp", "", 2000, G, 1, "staples", Z, 3299),
    MP("mk-beans-dry-500g", "Karoo Kitchen", "Sugar beans", "dried", 500, G, 1, "staples", Z, 3299),
    MP("mk-sugar-2.5kg", "Sunbird", "White sugar", "", 2500, G, 1, "staples", S, 5499),
    MP("mk-sugar-brown-2kg", "Sunbird", "Brown sugar", "", 2000, G, 1, "staples", S, 4499),
    MP("mk-oil-2l", "Sunbird", "Sunflower oil", "", 2000, ML, 1, "staples", Z, 6499),
    MP("mk-oil-5l", "Sunbird", "Sunflower oil", "", 5000, ML, 1, "staples", Z, 15499),
    MP("mk-flour-2.5kg", "Highveld Mills", "Cake flour", "", 2500, G, 1, "staples", S, 3999),
    MP("mk-pasta-500g", "Karoo Kitchen", "Spaghetti", "", 500, G, 1, "staples", S, 2199),
    MP("mk-macaroni-500g", "Karoo Kitchen", "Macaroni", "", 500, G, 1, "staples", S, 2199),
    MP("mk-oats-1kg", "Karoo Kitchen", "Rolled oats", "", 1000, G, 1, "breakfast", S, 3999),
    MP("mk-cornflakes-750g", "Sunbird", "Corn flakes", "", 750, G, 1, "breakfast", S, 5999),
    MP("mk-wheat-bisc-450g", "Sunbird", "Wheat biscuits", "", 450, G, 1, "breakfast", S, 4999),
    # Bakery and dairy
    MP("mk-bread-brown", "Bakers Lane", "Brown bread", "sliced", 700, G, 1, "bakery", Z, 1999),
    MP("mk-bread-white", "Bakers Lane", "White bread", "sliced", 700, G, 1, "bakery", S, 2199),
    MP("mk-milk-2l", "Veld Valley", "Fresh milk", "full cream", 2000, ML, 1, "dairy", Z, 3699),
    MP("mk-milk-uht-6", "Veld Valley", "UHT milk", "full cream", 1000, ML, 6, "dairy", Z, 10999),
    MP("mk-eggs-18", "Hen House", "Large eggs", "", 18, EA, 1, "dairy", Z, 6499),
    MP("mk-eggs-30", "Hen House", "Large eggs", "tray", 30, EA, 1, "dairy", Z, 9999),
    MP("mk-butter-500g", "Veld Valley", "Butter", "salted", 500, G, 1, "dairy", S, 8999),
    MP("mk-marg-500g", "Sunbird", "Margarine spread", "", 500, G, 1, "dairy", S, 3499),
    MP("mk-cheese-900g", "Veld Valley", "Cheddar cheese", "", 900, G, 1, "dairy", S, 13999),
    MP("mk-yoghurt-1kg", "Veld Valley", "Plain yoghurt", "", 1000, G, 1, "dairy", S, 3999),
    # Meat
    MP("mk-chicken-2kg", "Plaas Poultry", "Frozen chicken portions", "mixed", 2000, G, 1, "meat", S, 9999),
    MP("mk-mince-500g", "Plaas Poultry", "Beef mince", "lean", 500, G, 1, "meat", S, 6999),
    MP("mk-wors-1kg", "Plaas Poultry", "Boerewors", "traditional", 1000, G, 1, "meat", S, 10999),
    MP("mk-polony-1kg", "Plaas Poultry", "Polony", "", 1000, G, 1, "meat", S, 4999),
    # Produce
    MP("mk-potatoes-7kg", "Farm Gate", "Potatoes", "pocket", 7000, G, 1, "produce", Z, 7999),
    MP("mk-onions-2kg", "Farm Gate", "Onions", "pocket", 2000, G, 1, "produce", Z, 3299),
    MP("mk-tomatoes-1kg", "Farm Gate", "Tomatoes", "", 1000, G, 1, "produce", Z, 2999),
    MP("mk-apples-1.5kg", "Farm Gate", "Apples", "bag", 1500, G, 1, "produce", Z, 3299),
    MP("mk-bananas-1kg", "Farm Gate", "Bananas", "", 1000, G, 1, "produce", Z, 2699),
    MP("mk-cabbage", "Farm Gate", "Cabbage", "whole", 1, EA, 1, "produce", Z, 1999),
    MP("mk-carrots-1kg", "Farm Gate", "Carrots", "", 1000, G, 1, "produce", Z, 1999),
    # Tins and pantry
    MP("mk-bakedbeans-410g", "Sunbird", "Baked beans", "in tomato sauce", 410, G, 1, "tins", S, 1899),
    MP("mk-pilchards-400g", "Ocean Cove", "Pilchards", "in tomato sauce", 400, G, 1, "tins", Z, 3299),
    MP("mk-tuna-170g", "Ocean Cove", "Tuna chunks", "in brine", 170, G, 1, "tins", S, 2999),
    MP("mk-chakalaka-410g", "Sunbird", "Chakalaka relish", "mild", 410, G, 1, "tins", S, 1799),
    MP("mk-peanut-400g", "Sunbird", "Peanut butter", "smooth", 400, G, 1, "pantry", S, 4299),
    MP("mk-jam-450g", "Sunbird", "Apricot jam", "", 450, G, 1, "pantry", S, 3999),
    MP("mk-mayo-750g", "Sunbird", "Mayonnaise", "", 750, G, 1, "pantry", S, 4999),
    MP("mk-tsauce-700ml", "Sunbird", "Tomato sauce", "", 700, ML, 1, "pantry", S, 3299),
    MP("mk-soup-400g", "Karoo Kitchen", "Soup powder", "brown onion", 400, G, 1, "pantry", S, 3499),
    MP("mk-stock-24", "Karoo Kitchen", "Stock cubes", "beef", 24, EA, 1, "pantry", S, 2999),
    MP("mk-atchar-380g", "Karoo Kitchen", "Mango atchar", "", 380, G, 1, "pantry", S, 2999),
    MP("mk-curry-100g", "Karoo Kitchen", "Curry powder", "medium", 100, G, 1, "pantry", S, 2499),
    # Beverages and snacks
    MP("mk-rooibos-80", "Karoo Kitchen", "Rooibos tea", "80 bags", 80, EA, 1, "beverages", S, 4499),
    MP("mk-blacktea-100", "Karoo Kitchen", "Black tea", "100 bags", 100, EA, 1, "beverages", S, 4999),
    MP("mk-coffee-inst-200g", "Karoo Kitchen", "Instant coffee", "", 200, G, 1, "beverages", S, 10999),
    MP("mk-creamer-1kg", "Veld Valley", "Coffee creamer", "", 1000, G, 1, "beverages", S, 5999),
    MP("mk-cola-2l", "Fizz Co", "Cola", "", 2000, ML, 1, "beverages", S, 2699),
    MP("mk-juice-1l", "Orchard Sun", "Fruit juice", "mango", 1000, ML, 1, "beverages", S, 2999),
    MP("mk-water-5l", "Berg Spring", "Still water", "", 5000, ML, 1, "beverages", S, 2299),
    MP("mk-chips-125g", "Crunch Co", "Maize snacks", "cheese", 125, G, 1, "snacks", S, 1799),
    MP("mk-biscuits-200g", "Crunch Co", "Tea biscuits", "", 200, G, 1, "snacks", S, 1999),
    # Baby
    MP("mk-formula-900g", "Little Ones", "Infant formula", "stage 1", 900, G, 1, "baby", S, 28999),
    MP("mk-nappies-jumbo", "Little Ones", "Nappies", "size 4 jumbo", 64, EA, 1, "baby", S, 19999),
    MP("mk-wipes-80", "Little Ones", "Baby wipes", "", 80, EA, 1, "baby", S, 4999),
    # Household and personal care
    MP("mk-dish-750ml", "Tsitsi Home", "Dishwashing liquid", "", 750, ML, 1, "household", S, 3299),
    MP("mk-washing-2kg", "Tsitsi Home", "Washing powder", "", 2000, G, 1, "household", S, 8999),
    MP("mk-softener-2l", "Tsitsi Home", "Fabric softener", "", 2000, ML, 1, "household", S, 4999),
    MP("mk-bleach-1.5l", "Tsitsi Home", "Bleach", "", 1500, ML, 1, "household", S, 3499),
    MP("mk-tissue-9", "Tsitsi Home", "Toilet tissue", "2-ply", 1, EA, 9, "household", S, 8999),
    MP("mk-refuse-20", "Tsitsi Home", "Refuse bags", "", 20, EA, 1, "household", S, 3999),
    MP("mk-soap-4", "Tsitsi Home", "Bath soap", "4 bars", 4, EA, 1, "personal", S, 3999),
    MP("mk-toothpaste-100ml", "Tsitsi Home", "Toothpaste", "", 100, ML, 1, "personal", S, 2999),
    MP("mk-jelly-250ml", "Tsitsi Home", "Petroleum jelly", "", 250, ML, 1, "personal", S, 3999),
    MP("mk-matches-10", "Flint", "Matches", "10 boxes", 10, EA, 1, "household", S, 1499),
    MP("mk-candles-6", "Flint", "Candles", "household", 6, EA, 1, "household", S, 3999),
    MP("mk-dogfood-8kg", "Good Boy", "Dry dog food", "adult", 8000, G, 1, "pets", S, 24999),
    # Load-shedding and hardware lines (grocers stock a few; hardware chains stock most)
    MP("mk-batteries-aa4", "Volta", "AA batteries", "alkaline", 4, EA, 1, "hardware", S, 5999),
    MP("mk-led-bulb-2", "Volta", "LED bulb 9W", "2-pack", 2, EA, 1, "hardware", S, 4999),
    MP("mk-lantern", "Volta", "Rechargeable LED lantern", "", 1, EA, 1, "hardware", S, 14999),
    MP("mk-gas-9kg", "Blue Flame", "LP gas refill", "9kg exchange", 9000, G, 1, "hardware", S, 39999),
    MP("mk-powerstation", "Volta", "Portable power station", "300Wh", 1, EA, 1, "hardware", S, 499999),
    MP("mk-cement-50kg", "Rockmix", "Cement", "general purpose", 50000, G, 1, "building", S, 10999),
    MP("mk-tile-adh-20kg", "Rockmix", "Tile adhesive", "", 20000, G, 1, "building", S, 14999),
    MP("mk-paint-20l", "Colourcraft", "PVA paint", "white", 20000, ML, 1, "building", S, 64999),
    MP("mk-roller", "Colourcraft", "Paint roller", "225mm", 1, EA, 1, "building", S, 3999),
    MP("mk-brush-50mm", "Colourcraft", "Paint brush", "50mm", 1, EA, 1, "building", S, 2999),
    MP("mk-screws-100", "Fixit", "Wood screws", "4x40mm", 100, EA, 1, "building", S, 4999),
    MP("mk-nails-1kg", "Fixit", "Wire nails", "75mm", 1000, G, 1, "building", S, 5999),
    MP("mk-silicone", "Fixit", "Silicone sealant", "clear", 280, ML, 1, "building", S, 7999),
    MP("mk-extension-5m", "Volta", "Extension cord", "5m", 1, EA, 1, "hardware", S, 16999),
    MP("mk-padlock-50mm", "Fixit", "Padlock", "50mm", 1, EA, 1, "hardware", S, 11999),
    MP("mk-hose-20m", "Fixit", "Garden hose", "20m", 1, EA, 1, "garden", S, 29999),
    MP("mk-wheelbarrow", "Fixit", "Wheelbarrow", "65L", 1, EA, 1, "garden", S, 79999),
]
# fmt: on

GROCERY = {
    "staples", "breakfast", "bakery", "dairy", "meat", "produce", "tins", "pantry",
    "beverages", "snacks", "baby", "household", "personal", "pets",
}  # fmt: skip
HARDWARE = {"hardware", "building", "garden"}
GROCER_HARDWARE = {"mk-batteries-aa4", "mk-led-bulb-2", "mk-lantern", "mk-gas-9kg"}


@dataclass(frozen=True)
class Branch:
    code: str
    name: str
    zones: tuple[str, ...]
    price_factor: float = 1.0  # franchise branches set their own prices


@dataclass(frozen=True)
class Chain:
    code: str
    name: str
    archetype: str
    categories: set[str]
    extra_products: set[str]
    price_index: float
    coverage: float  # share of in-range products a branch actually lists
    minimum_order_minor: int
    delivery_fee_minor: int
    pick_minutes: int
    first_slot_minutes: int
    slot_capacity: int
    branches: tuple[Branch, ...]
    category_index: dict[str, float] = field(default_factory=dict)


# fmt: off
CHAINS = [
    Chain(
        "zest", "Zest Express (Fictional)",
        "app-first rapid delivery: nearest branch, ~60 minutes, premium prices",
        GROCERY, GROCER_HARDWARE, 1.06, 0.92, 0, 3500, 15, 40, 6,
        (
            Branch("zest-sandton", "Zest Express Sandton", ("gp-sandton",)),
            Branch("zest-soweto", "Zest Express Soweto", ("gp-soweto",)),
            Branch("zest-menlyn", "Zest Express Pretoria East", ("gp-pretoria-east",)),
            Branch("zest-midrand", "Zest Express Midrand", ("gp-midrand", "gp-tembisa")),
            Branch("zest-cityb", "Zest Express City Bowl", ("wc-city-bowl",)),
            Branch("zest-bellville", "Zest Express Bellville", ("wc-bellville",)),
            Branch("zest-umhlanga", "Zest Express Umhlanga", ("kzn-umhlanga",)),
        ),
        category_index={"produce": 1.10, "meat": 1.08},
    ),
    Chain(
        "fairbasket", "Fairbasket Supermarkets (Fictional)",
        "national mid-market supermarket: scheduled delivery, loyalty-card prices",
        GROCERY, GROCER_HARDWARE, 1.00, 0.95, 0, 5000, 45, 180, 8,
        (
            Branch("fb-rosebank", "Fairbasket Rosebank", ("gp-sandton", "gp-midrand")),
            Branch("fb-jabulani", "Fairbasket Jabulani", ("gp-soweto",)),
            Branch("fb-hatfield", "Fairbasket Hatfield", ("gp-pretoria-east",)),
            Branch("fb-tembisa", "Fairbasket Tembisa", ("gp-tembisa",)),
            Branch("fb-claremont", "Fairbasket Claremont", ("wc-city-bowl", "wc-bellville")),
            Branch("fb-umhlanga", "Fairbasket Gateway", ("kzn-umhlanga",)),
            Branch("fb-walmer", "Fairbasket Walmer", ("ec-gqeberha",)),
        ),
    ),
    Chain(
        "cornertree", "Corner Tree Market (Fictional)",
        "owner-run franchise: each branch sets its own prices, minimum order",
        GROCERY, {"mk-batteries-aa4", "mk-candles-6"}, 1.04, 0.80, 15000, 4000, 30, 120, 5,
        (
            Branch("ct-bryanston", "Corner Tree Bryanston", ("gp-sandton",), 1.12),
            Branch("ct-protea", "Corner Tree Protea Glen", ("gp-soweto",), 0.97),
            Branch("ct-faerie", "Corner Tree Faerie Glen", ("gp-pretoria-east",), 1.06),
            Branch("ct-kyalami", "Corner Tree Kyalami", ("gp-midrand",), 1.03),
            Branch("ct-gardens", "Corner Tree Gardens", ("wc-city-bowl",), 1.10),
            Branch("ct-durbanville", "Corner Tree Durbanville", ("wc-bellville",), 1.01),
            Branch("ct-umlazi", "Corner Tree Umlazi", ("kzn-umlazi",), 0.98),
            Branch("ct-newtonpark", "Corner Tree Newton Park", ("ec-gqeberha",), 1.00),
        ),
    ),
    Chain(
        "thrift", "Thrift Depot (Fictional)",
        "discount staples: narrow range, lowest shelf prices, high minimum, slow",
        {"staples", "tins", "pantry", "household", "personal", "dairy", "bakery", "beverages"},
        {"mk-candles-6", "mk-matches-10"}, 0.90, 0.70, 20000, 3000, 90, 360, 6,
        (
            Branch("td-soweto", "Thrift Depot Soweto", ("gp-soweto",)),
            Branch("td-tembisa", "Thrift Depot Tembisa", ("gp-tembisa", "gp-midrand")),
            Branch("td-khaya", "Thrift Depot Khayelitsha", ("wc-khayelitsha", "wc-bellville")),
            Branch("td-umlazi", "Thrift Depot Umlazi", ("kzn-umlazi",)),
            Branch("td-motherwell", "Thrift Depot Motherwell", ("ec-gqeberha",)),
        ),
    ),
    Chain(
        "brickline", "Brickline Hardware (Fictional)",
        "big-box hardware warehouse: building and DIY, some cleaning lines, next-day delivery",
        HARDWARE, {"mk-candles-6", "mk-refuse-20", "mk-bleach-1.5l"}, 1.00, 0.95, 0, 15000, 120,
        1080, 4,
        (
            Branch("bl-northriding", "Brickline North", ("gp-sandton", "gp-midrand", "gp-tembisa")),
            Branch("bl-crossroads", "Brickline Crossroads", ("gp-soweto",)),
            Branch("bl-centurion", "Brickline Centurion", ("gp-pretoria-east",)),
            Branch("bl-montague", "Brickline Montague", ("wc-city-bowl", "wc-bellville", "wc-khayelitsha")),
            Branch("bl-springfield", "Brickline Springfield", ("kzn-umhlanga", "kzn-umlazi")),
        ),
        category_index={"building": 1.02},
    ),
    Chain(
        "yardstick", "Yardstick Build (Fictional)",
        "franchise building-supply yard: cheaper bulk materials, township coverage",
        HARDWARE, set(), 0.97, 0.75, 0, 25000, 180, 1440, 3,
        (
            Branch("ys-orlando", "Yardstick Orlando", ("gp-soweto",), 0.96),
            Branch("ys-tembisa", "Yardstick Tembisa", ("gp-tembisa",), 0.98),
            Branch("ys-khaya", "Yardstick Khayelitsha", ("wc-khayelitsha",), 0.97),
            Branch("ys-umlazi", "Yardstick Umlazi", ("kzn-umlazi",), 0.95),
            Branch("ys-motherwell", "Yardstick Motherwell", ("ec-gqeberha",), 1.00),
        ),
        category_index={"building": 0.92, "garden": 1.05},
    ),
]
# fmt: on


def _unit(*parts: str) -> float:
    """Deterministic pseudo-random number in [0, 1) from the given parts."""
    digest = hashlib.sha256(":".join(parts).encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _round_price(cents: float) -> int:
    """Round to a shelf-style price ending in 99 cents."""
    rands = max(1, round(cents / 100))
    return rands * 100 - 1


def listing(chain: Chain, branch: Branch, p: MP) -> tuple[int, int] | None:
    """(price, stock) for a product at a branch, or None when the branch does not list it."""
    in_range = p.category in chain.categories or p.code in chain.extra_products
    if not in_range or _unit("list", branch.code, p.code) >= chain.coverage:
        return None
    noise = 0.94 + 0.12 * _unit("price", branch.code, p.code)  # +/-6% item-level variation
    factor = chain.price_index * chain.category_index.get(p.category, 1.0) * branch.price_factor
    price = _round_price(p.base * factor * noise)
    r = _unit("stock", branch.code, p.code)
    stock = 0 if r < 0.04 else (2 if r < 0.12 else 6 + int(r * 60))
    if p.category in HARDWARE and p.base > 100000:
        stock = min(stock, 3)
    return price, stock


def seed_market(session: Session, *, now: datetime) -> dict[str, uuid.UUID]:
    """Ensure the market exists with fresh offers and slots as of `now`. Idempotent."""
    ids: dict[str, uuid.UUID] = {}
    for i, p in enumerate(MARKET_PRODUCTS):
        pid = sid("product", p.code)
        ids[f"product:{p.code}"] = pid
        _ensure(
            session,
            Product,
            pid,
            id=pid,
            gtin=gtin13(f"2100000{i + 1:05d}"),
            brand=p.brand,
            name=p.name,
            variant=p.variant,
            unit_measure=p.measure,
            unit=p.unit,
            pack_count=p.pack,
            category=p.category,
        )
    for chain in CHAINS:
        mid = sid("merchant", chain.code)
        ids[f"merchant:{chain.code}"] = mid
        _ensure(
            session,
            Merchant,
            mid,
            id=mid,
            code=chain.code,
            display_name=chain.name,
            legal_name=f"{chain.name} (synthetic entity)",
            state=MerchantState.PAYMENT_ENABLED,
            payout_destination_version=f"sim-payout-{chain.code}-v1",
        )
        for branch in chain.branches:
            lid = sid("location", branch.code)
            ids[f"location:{branch.code}"] = lid
            _ensure(
                session,
                MerchantLocation,
                lid,
                id=lid,
                merchant_id=mid,
                code=branch.code,
                name=f"{branch.name} (Fictional)",
                service_zones=list(branch.zones),
                minimum_order_minor=chain.minimum_order_minor,
                pick_minutes=chain.pick_minutes,
            )
            if (
                session.scalars(
                    select(MerchantCapability.id).where(MerchantCapability.location_id == lid)
                ).first()
                is None
            ):
                session.add(
                    MerchantCapability(
                        location_id=lid,
                        version=1,
                        can_reserve=True,
                        can_commit=True,
                        can_cancel=True,
                        can_lookup_by_reference=True,
                        reservation_ttl_seconds=1800,
                        evidence="synthetic merchant simulator; not evidence of any real merchant",
                    )
                )
            _seed_offers(session, chain, branch, mid, lid, now)
            _seed_slots(session, chain, branch, lid, now)
    session.flush()
    _seed_promotions(session, ids, now)
    session.flush()
    return ids


def _seed_offers(session, chain, branch, mid, lid, now) -> None:
    for p in MARKET_PRODUCTS:
        listed = listing(chain, branch, p)
        if listed is None:
            continue
        price, stock = listed
        pid = sid("product", p.code)
        sku = f"{chain.code.upper()}-{p.code.upper()}"
        if (
            session.scalars(
                select(ProductMapping.id).where(
                    ProductMapping.merchant_id == mid,
                    ProductMapping.merchant_sku == sku,
                    ProductMapping.active,
                )
            ).first()
            is None
        ):
            session.add(
                ProductMapping(
                    merchant_id=mid,
                    merchant_sku=sku,
                    product_id=pid,
                    match_level=MatchLevel.GTIN_VERIFIED,
                    evidence="synthetic GTIN match",
                )
            )
        latest = session.scalars(
            select(OfferVersion.valid_until)
            .where(OfferVersion.location_id == lid, OfferVersion.product_id == pid)
            .order_by(OfferVersion.observed_at.desc())
            .limit(1)
        ).first()
        if latest is not None and latest >= now + timedelta(hours=12):
            continue
        session.add(
            OfferVersion(
                location_id=lid,
                product_id=pid,
                merchant_sku=sku,
                price_minor=price,
                tax_code=p.tax,
                stock_quantity=stock,
                stock_confidence=StockConfidence.OBSERVED if stock > 2 else StockConfidence.LOW,
                observed_at=now - timedelta(minutes=5),
                valid_until=now + timedelta(days=2),
                description=f"{p.brand} {p.name} (synthetic listing)",
            )
        )


def _seed_slots(session, chain, branch, lid, now) -> None:
    for zone in branch.zones:
        spare = session.scalar(
            select(func.coalesce(func.sum(DeliverySlot.capacity - DeliverySlot.booked), 0)).where(
                DeliverySlot.location_id == lid,
                DeliverySlot.zone == zone,
                DeliverySlot.starts_at > now + timedelta(minutes=chain.pick_minutes),
            )
        )
        if spare >= chain.slot_capacity * 2:
            continue
        # The home branch's zone is closest; other zones it serves cost a little more.
        surcharge = 0 if zone == branch.zones[0] else 1000
        for hour in range(12):
            start = now + timedelta(minutes=chain.first_slot_minutes + 60 * hour)
            session.add(
                DeliverySlot(
                    location_id=lid,
                    courier_code=COURIER,
                    zone=zone,
                    starts_at=start,
                    ends_at=start + timedelta(hours=1),
                    fee_minor=chain.delivery_fee_minor + surcharge,
                    capacity=chain.slot_capacity,
                )
            )


def _seed_promotions(session: Session, ids: dict[str, uuid.UUID], now: datetime) -> None:
    window = {"valid_from": now - timedelta(days=1), "valid_until": now + timedelta(days=7)}

    def product(code):
        return ids[f"product:{code}"]

    promos = []
    for chain in CHAINS:
        for branch in chain.branches:
            loc = ids[f"location:{branch.code}"]
            if chain.code == "fairbasket":
                promos += [
                    dict(location_id=loc, kind=PromotionKind.DELIVERY_THRESHOLD,
                         min_spend_minor=60000),
                    dict(location_id=loc, kind=PromotionKind.LOYALTY_PRICE,
                         product_ids=[product("mk-oil-2l")], price_minor=5499,
                         requires_loyalty_programme="fairbasket-smart-fictional"),
                    dict(location_id=loc, kind=PromotionKind.MULTIBUY,
                         product_ids=[product("mk-pilchards-400g")], min_quantity=3,
                         bundle_price_minor=8500),
                ]  # fmt: skip
            elif chain.code == "zest":
                promos += [
                    dict(location_id=loc, kind=PromotionKind.PERCENT_LINE,
                         product_ids=[product("mk-coffee-inst-200g")], percent_bp=1500),
                    dict(location_id=loc, kind=PromotionKind.DELIVERY_THRESHOLD,
                         min_spend_minor=45000),
                ]  # fmt: skip
            elif chain.code == "cornertree":
                promos.append(
                    dict(location_id=loc, kind=PromotionKind.MULTIBUY,
                         product_ids=[product("mk-cola-2l")], min_quantity=2,
                         bundle_price_minor=4500)
                )  # fmt: skip
            elif chain.code == "brickline":
                promos.append(
                    dict(location_id=loc, kind=PromotionKind.DELIVERY_THRESHOLD,
                         min_spend_minor=150000)
                )  # fmt: skip
            elif chain.code == "yardstick":
                promos.append(
                    dict(location_id=loc, kind=PromotionKind.MULTIBUY,
                         product_ids=[product("mk-cement-50kg")], min_quantity=10,
                         bundle_price_minor=95000)
                )  # fmt: skip
    for promo in promos:
        active = session.scalars(
            select(Promotion.id).where(
                Promotion.location_id == promo["location_id"],
                Promotion.kind == promo["kind"],
                Promotion.valid_until > now + timedelta(days=1),
            )
        ).first()
        if active is None:
            session.add(Promotion(**promo, **window))

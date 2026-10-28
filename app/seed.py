"""Deterministic synthetic seed: fictional merchants, brands, catalogue, stock and slots.

Every name here is invented and labelled fictional. GTINs use the GS1 restricted-
circulation prefix 2 so they cannot collide with real products. Prices are
illustrative synthetic data, VAT-inclusive, in cents.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.delivery.models import DeliverySlot
from app.merchants.models import Merchant, MerchantCapability, MerchantLocation, MerchantState
from app.offers.models import OfferVersion, Promotion, PromotionKind, StockConfidence, TaxCode
from app.products.models import MatchLevel, Product, ProductMapping, Unit

NAMESPACE = uuid.UUID("6f1c2a8e-2d0b-4f5e-9a51-7c3f1b0d9e42")
COURIER = "swiftparcel-fictional"
ZONES = ("zone-a", "zone-b")


def sid(*parts: str) -> uuid.UUID:
    """Stable id so the seed is reproducible across runs and machines."""
    return uuid.uuid5(NAMESPACE, ":".join(parts))


def gtin13(body12: str) -> str:
    digits = [int(c) for c in body12]
    total = sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits))
    return body12 + str((10 - total % 10) % 10)


@dataclass(frozen=True)
class P:
    code: str
    brand: str
    name: str
    variant: str
    measure: int
    unit: Unit
    pack: int
    category: str
    tax: TaxCode


# fmt: off
PRODUCTS = [
    P("milk-1l", "Veld Valley", "UHT milk", "full cream", 1000, Unit.ML, 1, "dairy", TaxCode.STANDARD),
    P("milk-6x1l", "Veld Valley", "UHT milk", "full cream", 1000, Unit.ML, 6, "dairy", TaxCode.STANDARD),
    P("milk-lf-1l", "Veld Valley", "UHT milk", "low fat", 1000, Unit.ML, 1, "dairy", TaxCode.STANDARD),
    P("maize-2.5kg", "Highveld Mills", "Super maize meal", "", 2500, Unit.G, 1, "staples", TaxCode.ZERO_RATED),
    P("maize-5kg", "Highveld Mills", "Super maize meal", "", 5000, Unit.G, 1, "staples", TaxCode.ZERO_RATED),
    P("rice-2kg", "Karoo Kitchen", "Long grain rice", "", 2000, Unit.G, 1, "staples", TaxCode.ZERO_RATED),
    P("sugar-2.5kg", "Sunbird", "White sugar", "", 2500, Unit.G, 1, "staples", TaxCode.STANDARD),
    P("oil-2l", "Sunbird", "Sunflower oil", "", 2000, Unit.ML, 1, "staples", TaxCode.ZERO_RATED),
    P("tea-100", "Karoo Kitchen", "Rooibos tea", "100 bags", 100, Unit.EACH, 1, "beverages", TaxCode.STANDARD),
    P("coffee-250g", "Karoo Kitchen", "Ground coffee", "medium roast", 250, Unit.G, 1, "beverages", TaxCode.STANDARD),
    P("beans-410g", "Sunbird", "Baked beans", "in tomato sauce", 410, Unit.G, 1, "tins", TaxCode.STANDARD),
    P("pasta-500g", "Karoo Kitchen", "Spaghetti", "", 500, Unit.G, 1, "staples", TaxCode.STANDARD),
    P("peanut-400g", "Sunbird", "Peanut butter", "smooth", 400, Unit.G, 1, "spreads", TaxCode.STANDARD),
    P("flour-2.5kg", "Highveld Mills", "Cake flour", "", 2500, Unit.G, 1, "staples", TaxCode.STANDARD),
    P("tomato-400g", "Sunbird", "Chopped tomatoes", "", 400, Unit.G, 1, "tins", TaxCode.STANDARD),
    P("dish-750ml", "Tsitsi Home", "Dishwashing liquid", "", 750, Unit.ML, 1, "household", TaxCode.STANDARD),
    P("tissue-9", "Tsitsi Home", "Toilet tissue", "2-ply", 1, Unit.EACH, 9, "household", TaxCode.STANDARD),
    P("washing-2kg", "Tsitsi Home", "Washing powder", "", 2000, Unit.G, 1, "household", TaxCode.STANDARD),
]
# fmt: on


@dataclass(frozen=True)
class M:
    code: str
    name: str
    zones: tuple[str, ...]
    pick_minutes: int
    minimum_order_minor: int
    delivery_fee_minor: int
    first_slot_minutes: int
    # product code -> (price, stock); absent products are not stocked.
    prices: dict[str, tuple[int, int]]


# fmt: off
MERCHANTS = [
    M("kestrel", "Kestrel Grocer (Fictional)", ZONES, 45, 0, 4500, 90, {
        "milk-1l": (1899, 40), "milk-6x1l": (9999, 10), "milk-lf-1l": (1899, 20),
        "maize-2.5kg": (3999, 30), "maize-5kg": (7499, 15), "rice-2kg": (4299, 25),
        "sugar-2.5kg": (5499, 30), "oil-2l": (6299, 20), "tea-100": (5999, 15),
        "coffee-250g": (8999, 10), "beans-410g": (1699, 60), "pasta-500g": (2199, 40),
        "peanut-400g": (3999, 20), "flour-2.5kg": (3799, 20), "tomato-400g": (1599, 50),
        "dish-750ml": (3299, 25), "tissue-9": (8999, 15), "washing-2kg": (9999, 10),
    }),
    M("baobab", "Baobab Market (Fictional)", ZONES, 60, 15000, 4000, 120, {
        "milk-1l": (1799, 30), "milk-6x1l": (9499, 8), "maize-2.5kg": (3699, 40),
        "maize-5kg": (6999, 20), "rice-2kg": (3999, 30), "sugar-2.5kg": (5299, 25),
        "oil-2l": (5999, 25), "beans-410g": (1599, 80), "pasta-500g": (1999, 50),
        "flour-2.5kg": (3599, 25), "tomato-400g": (1499, 60), "tissue-9": (8499, 20),
    }),
    M("umoya", "Umoya Foods (Fictional)", ("zone-a",), 20, 0, 5500, 45, {
        "milk-1l": (2099, 25), "milk-6x1l": (11499, 6), "milk-lf-1l": (2099, 15),
        "rice-2kg": (4699, 15), "sugar-2.5kg": (5899, 15), "oil-2l": (6799, 15),
        "tea-100": (6299, 10), "coffee-250g": (9499, 10), "beans-410g": (1899, 30),
        "pasta-500g": (2399, 25), "peanut-400g": (4299, 15), "dish-750ml": (3499, 20),
        "washing-2kg": (10499, 8),
    }),
    M("jacaranda", "Jacaranda Pantry (Fictional)", ("zone-b",), 50, 10000, 3500, 150, {
        "milk-1l": (1949, 20), "maize-2.5kg": (3899, 20), "rice-2kg": (4199, 20),
        "sugar-2.5kg": (5399, 20), "oil-2l": (6199, 20), "tea-100": (5799, 10),
        "coffee-250g": (8799, 10), "beans-410g": (1649, 40), "peanut-400g": (3899, 15),
        "dish-750ml": (3199, 15), "tissue-9": (8799, 10),
    }),
]
# fmt: on


def seed(session: Session, *, now: datetime) -> dict[str, uuid.UUID]:
    """Create the synthetic catalogue as of `now`. Re-running is a no-op."""
    ids: dict[str, uuid.UUID] = {}
    if session.get(Merchant, sid("merchant", "kestrel")) is not None:
        for p in PRODUCTS:
            ids[f"product:{p.code}"] = sid("product", p.code)
        for m in MERCHANTS:
            ids[f"merchant:{m.code}"] = sid("merchant", m.code)
            ids[f"location:{m.code}"] = sid("location", m.code)
        return ids

    for i, p in enumerate(PRODUCTS):
        pid = sid("product", p.code)
        ids[f"product:{p.code}"] = pid
        session.add(
            Product(
                id=pid,
                gtin=gtin13(f"2000000{i + 1:05d}"),
                brand=p.brand,
                name=p.name,
                variant=p.variant,
                unit_measure=p.measure,
                unit=p.unit,
                pack_count=p.pack,
                category=p.category,
            )
        )
    session.flush()

    for m in MERCHANTS:
        mid, lid = sid("merchant", m.code), sid("location", m.code)
        ids[f"merchant:{m.code}"], ids[f"location:{m.code}"] = mid, lid
        session.add(
            Merchant(
                id=mid,
                code=m.code,
                display_name=m.name,
                legal_name=f"{m.name} (synthetic entity)",
                state=MerchantState.PAYMENT_ENABLED,
                payout_destination_version=f"sim-payout-{m.code}-v1",
            )
        )
        session.flush()
        session.add(
            MerchantLocation(
                id=lid,
                merchant_id=mid,
                code=m.code,
                name=f"{m.name} - Central",
                service_zones=list(m.zones),
                minimum_order_minor=m.minimum_order_minor,
                pick_minutes=m.pick_minutes,
            )
        )
        session.flush()
        session.add(
            MerchantCapability(
                location_id=lid,
                version=1,
                can_reserve=True,
                can_commit=True,
                can_cancel=True,
                can_lookup_by_reference=True,
                reservation_ttl_seconds=1800,
                evidence="synthetic merchant simulator; not evidence of any real merchant capability",
            )
        )
        for code, (price, stock) in m.prices.items():
            product = next(p for p in PRODUCTS if p.code == code)
            sku = f"{m.code.upper()}-{code.upper()}"
            session.add(
                ProductMapping(
                    merchant_id=mid,
                    merchant_sku=sku,
                    product_id=sid("product", code),
                    match_level=MatchLevel.GTIN_VERIFIED,
                    evidence="synthetic GTIN match",
                )
            )
            session.add(
                OfferVersion(
                    location_id=lid,
                    product_id=sid("product", code),
                    merchant_sku=sku,
                    price_minor=price,
                    tax_code=product.tax,
                    stock_quantity=stock,
                    stock_confidence=StockConfidence.OBSERVED,
                    observed_at=now - timedelta(minutes=5),
                    valid_until=now + timedelta(days=2),
                    description=f"{product.brand} {product.name} (synthetic listing)",
                )
            )
        for hour in range(12):
            start = now + timedelta(minutes=m.first_slot_minutes + 60 * hour)
            for zone in m.zones:
                session.add(
                    DeliverySlot(
                        location_id=lid,
                        courier_code=COURIER,
                        zone=zone,
                        starts_at=start,
                        ends_at=start + timedelta(hours=1),
                        fee_minor=m.delivery_fee_minor,
                        capacity=5,
                    )
                )
    session.flush()

    # Structured promotions (D-S03.3).
    window = {"valid_from": now - timedelta(days=1), "valid_until": now + timedelta(days=7)}
    session.add_all(
        [
            Promotion(
                location_id=ids["location:kestrel"],
                kind=PromotionKind.DELIVERY_THRESHOLD,
                min_spend_minor=80000,
                **window,
            ),
            Promotion(
                location_id=ids["location:baobab"],
                kind=PromotionKind.MULTIBUY,
                product_ids=[ids["product:beans-410g"]],
                min_quantity=3,
                bundle_price_minor=4200,
                **window,
            ),
            Promotion(
                location_id=ids["location:umoya"],
                kind=PromotionKind.PERCENT_LINE,
                product_ids=[ids["product:coffee-250g"]],
                percent_bp=1000,
                **window,
            ),
            Promotion(
                location_id=ids["location:jacaranda"],
                kind=PromotionKind.LOYALTY_PRICE,
                product_ids=[ids["product:oil-2l"]],
                price_minor=4999,
                requires_loyalty_programme="jacaranda-rewards-fictional",
                **window,
            ),
        ]
    )
    session.flush()
    return ids


def location_ids(session: Session) -> dict[str, uuid.UUID]:
    return {
        code: lid
        for code, lid in session.execute(select(MerchantLocation.code, MerchantLocation.id))
    }

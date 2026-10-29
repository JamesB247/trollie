"""Build an optimiser Problem from authoritative records (never from agent-supplied prices)."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.delivery.models import DeliverySlot
from app.merchants.models import MerchantLocation
from app.offers.service import active_promotions, orderable_offers
from app.products.models import Product
from app.quotes.optimiser import LineRequest, Location, Offer, Problem, ProductInfo, Promo, Slot

SERVICE_FEE_MINOR = 2000  # synthetic customer service fee (blueprint §10.4 example)


def build_problem(
    session: Session,
    *,
    lines: list[LineRequest],
    zone: str,
    now: datetime,
    loyalty_programmes: frozenset[str] = frozenset(),
    deadline: datetime | None = None,
    budget_minor: int | None = None,
    allow_omit_optional: bool = False,
    unavailable_locations: frozenset[uuid.UUID] = frozenset(),
) -> Problem:
    from app.merchants.risk import over_exposure_cap

    product_ids = {c.product_id for ln in lines for c in ln.candidates}
    capped = over_exposure_cap(session)  # I-044: new merchants holding too much undelivered
    offers = [
        o
        for o in orderable_offers(session, product_ids=product_ids, zone=zone, now=now)
        if o.merchant_id not in capped and o.location_id not in unavailable_locations
    ]
    location_ids = {o.location_id for o in offers}
    locations = {
        loc.id: Location(
            loc.id, loc.merchant_id, loc.code, loc.minimum_order_minor, loc.pick_minutes
        )
        for loc in session.scalars(
            select(MerchantLocation).where(MerchantLocation.id.in_(location_ids))
        )
    }
    products = {
        p.id: ProductInfo(p.id, p.unit, p.total_measure)
        for p in session.scalars(select(Product).where(Product.id.in_(product_ids)))
    }
    slots = tuple(
        Slot(s.id, s.location_id, s.starts_at, s.ends_at, s.fee_minor, s.capacity - s.booked)
        for s in session.scalars(
            select(DeliverySlot).where(
                DeliverySlot.location_id.in_(location_ids),
                DeliverySlot.zone == zone,
                DeliverySlot.starts_at > now,
            )
        )
    )
    promos = tuple(
        Promo(
            promotion_id=p.id,
            location_id=p.location_id,
            kind=p.kind,
            product_ids=frozenset(p.product_ids or []),
            min_quantity=p.min_quantity,
            min_spend_minor=p.min_spend_minor,
            benefit_minor=p.benefit_minor,
            percent_bp=p.percent_bp,
            bundle_price_minor=p.bundle_price_minor,
            price_minor=p.price_minor,
            requires_loyalty_programme=p.requires_loyalty_programme,
        )
        for p in active_promotions(session, location_ids=location_ids, now=now)
    )
    return Problem(
        lines=tuple(lines),
        products=products,
        offers=tuple(
            Offer(o.offer_version_id, o.location_id, o.product_id, o.price_minor, o.stock_quantity)
            for o in offers
        ),
        locations=locations,
        slots=slots,
        promotions=promos,
        loyalty_programmes=loyalty_programmes,
        now=now,
        deadline=deadline,
        service_fee_minor=SERVICE_FEE_MINOR,
        budget_minor=budget_minor,
        allow_omit_optional=allow_omit_optional,
    )


def offer_ids(problem: Problem) -> set[uuid.UUID]:
    return {o.offer_version_id for o in problem.offers}

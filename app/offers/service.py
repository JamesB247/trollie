"""Orderable offer lookup (blueprint §11.1-11.2, §12.4).

An offer is orderable only when every one of these holds:
- the merchant is payment-enabled and the location serves the destination zone;
- the merchant SKU has an active mapping at an orderable match level;
- the product is ambient and not regulated (pilot category scope);
- the observation is still valid and does not report zero stock.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.merchants.models import Merchant, MerchantLocation, MerchantState
from app.offers.models import OfferVersion, Promotion
from app.products.models import ORDERABLE_MATCH_LEVELS, Product, ProductMapping


@dataclass(frozen=True)
class OfferView:
    offer_version_id: uuid.UUID
    location_id: uuid.UUID
    merchant_id: uuid.UUID
    product_id: uuid.UUID
    merchant_sku: str
    price_minor: int
    tax_code: str
    stock_quantity: int | None
    stock_confidence: str
    observed_at: datetime
    valid_until: datetime
    match_level: str


def orderable_offers(
    session: Session, *, product_ids: set[uuid.UUID], zone: str, now: datetime
) -> list[OfferView]:
    latest = (
        select(OfferVersion.id)
        .distinct(OfferVersion.location_id, OfferVersion.product_id)
        .where(OfferVersion.product_id.in_(product_ids), OfferVersion.observed_at <= now)
        .order_by(
            OfferVersion.location_id, OfferVersion.product_id, OfferVersion.observed_at.desc()
        )
        .subquery()
    )
    rows = session.execute(
        select(OfferVersion, MerchantLocation, ProductMapping)
        .join(latest, latest.c.id == OfferVersion.id)
        .join(MerchantLocation, MerchantLocation.id == OfferVersion.location_id)
        .join(Merchant, Merchant.id == MerchantLocation.merchant_id)
        .join(Product, Product.id == OfferVersion.product_id)
        .join(
            ProductMapping,
            and_(
                ProductMapping.merchant_id == Merchant.id,
                ProductMapping.merchant_sku == OfferVersion.merchant_sku,
                ProductMapping.active,
            ),
        )
        .where(
            Merchant.state == MerchantState.PAYMENT_ENABLED,
            MerchantLocation.service_zones.any(zone),
            ProductMapping.product_id == OfferVersion.product_id,
            ProductMapping.match_level.in_([m.value for m in ORDERABLE_MATCH_LEVELS]),
            Product.ambient,
            Product.regulated.is_(False),
            OfferVersion.valid_until > now,
        )
        .order_by(MerchantLocation.code, OfferVersion.product_id)
    ).all()
    return [
        OfferView(
            offer_version_id=o.id,
            location_id=o.location_id,
            merchant_id=loc.merchant_id,
            product_id=o.product_id,
            merchant_sku=o.merchant_sku,
            price_minor=o.price_minor,
            tax_code=o.tax_code,
            stock_quantity=o.stock_quantity,
            stock_confidence=o.stock_confidence,
            observed_at=o.observed_at,
            valid_until=o.valid_until,
            match_level=m.match_level,
        )
        for o, loc, m in rows
        if o.stock_quantity is None or o.stock_quantity > 0
    ]


def active_promotions(
    session: Session, *, location_ids: set[uuid.UUID], now: datetime
) -> list[Promotion]:
    return list(
        session.scalars(
            select(Promotion)
            .where(
                Promotion.location_id.in_(location_ids),
                Promotion.valid_from <= now,
                Promotion.valid_until > now,
            )
            .order_by(Promotion.location_id, Promotion.id)
        )
    )

"""Order-flow scaffolding: a two-store world in its own zone, and a purchase helper."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.delivery.models import DeliverySlot
from app.ledger import chart
from app.ledger.models import LedgerEntry
from app.ledger.service import account, balance
from app.merchants.models import Merchant, MerchantCapability, MerchantLocation, MerchantState
from app.offers.models import OfferVersion, StockConfidence
from app.orders.handlers import pump
from app.orders.service import create_order, start_checkout
from app.products.models import MatchLevel, Product, ProductMapping
from app.quotes.models import FulfilmentMode
from app.seed import COURIER, sid
from tests.flows import approve, estimate, firm, new_customer, register_passkey, shopping_list

ZONE = "zone-t"
SPLIT_PRODUCTS = {
    "a-rice": ("a", 4000),
    "a-oil": ("a", 6000),
    "b-tea": ("b", 3000),
    "b-jam": ("b", 2500),
}


def seed_split_world(session: Session, *, now: datetime) -> dict[str, uuid.UUID]:
    ids: dict[str, uuid.UUID] = {}
    if session.get(Merchant, sid("merchant", "split-a")) is not None:
        for code in SPLIT_PRODUCTS:
            ids[f"product:{code}"] = sid("product", f"split-{code}")
        for m in "ab":
            ids[f"merchant:{m}"] = sid("merchant", f"split-{m}")
            ids[f"location:{m}"] = sid("location", f"split-{m}")
        return ids
    for m, fee in (("a", 4000), ("b", 3000)):
        mid, lid = sid("merchant", f"split-{m}"), sid("location", f"split-{m}")
        ids[f"merchant:{m}"], ids[f"location:{m}"] = mid, lid
        session.add(
            Merchant(
                id=mid,
                code=f"split-{m}",
                display_name=f"Split {m.upper()} (Fictional)",
                legal_name=f"Split {m.upper()} (synthetic entity)",
                state=MerchantState.PAYMENT_ENABLED,
            )
        )
        session.flush()
        session.add(
            MerchantLocation(
                id=lid,
                merchant_id=mid,
                code=f"split-{m}",
                name=f"Split {m.upper()}",
                service_zones=[ZONE],
                pick_minutes=10,
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
                evidence="synthetic",
            )
        )
        for hour in range(6):
            start = now + timedelta(minutes=60 + 60 * hour)
            session.add(
                DeliverySlot(
                    location_id=lid,
                    courier_code=COURIER,
                    zone=ZONE,
                    starts_at=start,
                    ends_at=start + timedelta(hours=1),
                    fee_minor=fee,
                    capacity=500,
                )
            )
    for code, (m, price) in SPLIT_PRODUCTS.items():
        pid = sid("product", f"split-{code}")
        ids[f"product:{code}"] = pid
        session.add(
            Product(
                id=pid,
                brand="Split Brand (Fictional)",
                name=code,
                unit_measure=1,
                unit="each",
                category="test",
            )
        )
        session.flush()
        sku = f"SPLIT-{code.upper()}"
        session.add(
            ProductMapping(
                merchant_id=ids[f"merchant:{m}"],
                merchant_sku=sku,
                product_id=pid,
                match_level=MatchLevel.GTIN_VERIFIED,
                evidence="synthetic",
            )
        )
        session.add(
            OfferVersion(
                location_id=ids[f"location:{m}"],
                product_id=pid,
                merchant_sku=sku,
                price_minor=price,
                tax_code="standard",
                stock_quantity=None,
                stock_confidence=StockConfidence.OBSERVED,
                observed_at=now - timedelta(minutes=5),
                valid_until=now + timedelta(days=2),
            )
        )
    session.flush()
    return ids


@dataclass
class Purchase:
    order_id: uuid.UUID
    checkout_ref: str | None
    customer: object
    quote: object


DEFAULT_ITEMS = [("a-rice", {"packs": 2}), ("a-oil", {}), ("b-tea", {})]


def approved(
    rt,
    db,
    world,
    *,
    items=None,
    funding="pay_per_order:card_auth_capture",
    mode=FulfilmentMode.COMPLETE_REQUIRED,
    omissions=None,
):
    customer = new_customer(db, zone=ZONE)
    session_id = shopping_list(db, world, customer, items or DEFAULT_ITEMS)
    est = estimate(db, customer, session_id, rt.clock)
    result = firm(
        rt.sessions,
        rt.merchant,
        customer,
        est.id,
        rt.clock,
        mode=mode,
        omissions=omissions,
        funding=funding,
    )
    assert result.quote is not None, result.blocking
    register_passkey(db, customer, rt.clock)
    approval = approve(db, customer, result.quote.id, rt.clock)
    return customer, result.quote, approval


def purchase(rt, db, world, *, start=True, **kw) -> Purchase:
    customer, quote, approval = approved(rt, db, world, **kw)
    order_id = create_order(rt, account_id=customer.account_id, approval_id=approval.id)
    ref = start_checkout(rt, account_id=customer.account_id, order_id=order_id) if start else None
    return Purchase(order_id, ref, customer, quote)


def pay(rt, ref: str, *, approve: bool = True) -> None:
    rt.payments.customer_completes(ref, approve=approve)
    pump(rt, rt.payments)


def ledger_net_zero(db: Session) -> bool:
    net = db.scalar(select(func.sum(LedgerEntry.debit_minor) - func.sum(LedgerEntry.credit_minor)))
    return (net or 0) == 0


def payable(db: Session, merchant_id: uuid.UUID) -> int:
    return balance(db, account(db, chart.MERCHANT_PAYABLE, merchant_id))

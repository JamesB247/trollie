"""Merchant trust after onboarding (I-043, I-044).

Onboarding checks can be fooled with forged documents, so a newly onboarded merchant starts
on probation and Trollie watches what it actually does with paid orders:

- a leg is *not handed over* when the merchant has accepted and been paid for it, but the
  courier has not collected it by the end of the delivery window plus a grace period;
- a probation merchant with too many legs not handed over, or too many non-delivery claims,
  is suspended automatically; a standard merchant is flagged for a person to review;
- while a probation merchant holds too much undelivered customer money, it is left out of
  new baskets (exposure cap);
- the customers of a suspended merchant are refunded for legs it never handed over without
  having to ask.

None of this is a substitute for KYB; it limits the damage when KYB fails.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.controls.models import Incident
from app.controls.service import audit
from app.merchants.models import Merchant, MerchantState
from app.orders.models import DeliveryJob, Order, OrderLeg

NOT_HANDED_OVER = ("ACCEPTED", "PICKING", "READY_FOR_COLLECTION")
OUTSTANDING = ("RESERVED", "COMMIT_REQUESTED", "UNKNOWN", *NOT_HANDED_OVER, "COLLECTED")
PAID_ORDER = ("COMMITTING", "FULFILLING", "PARTIAL", "NEEDS_ATTENTION", "COMPENSATING")
PROBATION_SUSPEND_AFTER = 3  # legs not handed over
PROBATION_CLAIMS_SUSPEND_AFTER = 2  # non-delivery claims
PROBATION_NEVER_DELIVERED_SUSPEND_AFTER = 2  # legs not handed over, with nothing ever delivered
STANDARD_REVIEW_AFTER = 10


def grace() -> timedelta:
    return timedelta(minutes=get_settings().delivery_grace_minutes)


def not_handed_over(s: Session, now: datetime, merchant_id: uuid.UUID | None = None):
    """Paid legs whose window ended more than the grace period ago, still at the merchant."""
    q = (
        select(OrderLeg)
        .join(Order, Order.id == OrderLeg.order_id)
        .where(
            OrderLeg.state.in_(NOT_HANDED_OVER),
            OrderLeg.window_end.is_not(None),
            OrderLeg.window_end < now - grace(),
            Order.state.in_(PAID_ORDER),
        )
    )
    if merchant_id is not None:
        q = q.where(OrderLeg.merchant_id == merchant_id)
    return list(s.scalars(q))


def collected(s: Session, leg: OrderLeg) -> bool:
    job = s.scalars(select(DeliveryJob).where(DeliveryJob.order_leg_id == leg.id)).first()
    return job is not None and job.state in ("COLLECTING", "IN_TRANSIT", "DELIVERED")


def claims_against(s: Session, merchant_id: uuid.UUID) -> int:
    """Non-delivery claims in the last day (database time, as incidents are stamped)."""
    return s.scalar(
        select(func.count())
        .select_from(Incident)
        .where(
            Incident.kind == "non_delivery_claim",
            Incident.details["merchant_id"].astext == str(merchant_id),
            Incident.created_at >= func.now() - timedelta(days=1),
        )
    )


def should_suspend(tier: str, *, stuck: int, claims: int, delivered: int) -> bool:
    """Automatic suspension applies to probation merchants only; a standard merchant with a
    bad day is flagged for a person instead."""
    return tier == "probation" and (
        stuck >= PROBATION_SUSPEND_AFTER
        or claims >= PROBATION_CLAIMS_SUSPEND_AFTER
        # A new merchant that has never delivered anything is suspended sooner.
        or (stuck >= PROBATION_NEVER_DELIVERED_SUSPEND_AFTER and delivered == 0)
    )


def evaluate(s: Session, merchant_id: uuid.UUID, now: datetime) -> str:
    """Suspend or flag a merchant on its delivery record. Returns the merchant's state."""
    merchant = s.get(Merchant, merchant_id, with_for_update=True)
    if merchant.state != MerchantState.PAYMENT_ENABLED:
        return merchant.state
    stuck = len(not_handed_over(s, now, merchant_id))
    claims = claims_against(s, merchant_id)
    delivered = s.scalar(
        select(func.count())
        .select_from(OrderLeg)
        .where(OrderLeg.merchant_id == merchant_id, OrderLeg.state == "DELIVERED")
    )
    if should_suspend(merchant.risk_tier, stuck=stuck, claims=claims, delivered=delivered):
        merchant.state = MerchantState.SUSPENDED
        s.add(
            Incident(
                kind="merchant_suspended",
                severity="high",
                details={
                    "merchant_id": str(merchant_id),
                    "code": merchant.code,
                    "legs_not_handed_over": str(stuck),
                    "non_delivery_claims": str(claims),
                    "legs_delivered_ever": str(delivered),
                },
            )
        )
        audit(
            s,
            actor="system:merchant-risk",
            action="merchant.suspend",
            object_type="merchant",
            object_id=merchant_id,
            note=f"probation: {stuck} legs not handed over, {claims} claims",
        )
    elif stuck >= STANDARD_REVIEW_AFTER:
        flagged = s.scalars(
            select(Incident.id).where(
                Incident.kind == "merchant_review",
                Incident.details["merchant_id"].astext == str(merchant_id),
                Incident.created_at >= func.now() - timedelta(days=1),
            )
        ).first()
        if flagged is None:
            s.add(
                Incident(
                    kind="merchant_review",
                    severity="medium",
                    details={"merchant_id": str(merchant_id), "legs_not_handed_over": str(stuck)},
                )
            )
    return merchant.state


def over_exposure_cap(s: Session) -> set[uuid.UUID]:
    """Probation merchants already holding as much undelivered customer money as allowed."""
    cap = get_settings().probation_exposure_cap_minor
    rows = s.execute(
        select(OrderLeg.merchant_id, func.sum(OrderLeg.goods_minor + OrderLeg.delivery_minor))
        .join(Order, Order.id == OrderLeg.order_id)
        .join(Merchant, Merchant.id == OrderLeg.merchant_id)
        .where(
            Merchant.risk_tier == "probation",
            OrderLeg.state.in_(OUTSTANDING),
            Order.state.in_(("PAYMENT_PENDING", *PAID_ORDER)),
        )
        .group_by(OrderLeg.merchant_id)
    ).all()
    return {merchant_id for merchant_id, total in rows if total >= cap}


def review_deliveries(rt) -> int:
    """Sweep step: flag overdue legs, evaluate their merchants, and refund the customers of
    suspended merchants. Returns the number of refunds started."""
    from app.reconciliation.service import open_case

    now = rt.clock.now()
    with rt.sessions() as s, s.begin():
        overdue = not_handed_over(s, now)
        merchants = {leg.merchant_id for leg in overdue}
        for leg in overdue:
            order = s.get(Order, leg.order_id, with_for_update=True)
            order.attention_reason = order.attention_reason or "delivery_overdue"
            open_case(
                s,
                dedupe_key=f"overdue:{leg.id}",
                case_type="leg_not_handed_over",
                refs={"order_id": str(order.id), "leg_id": leg.leg_id,
                      "merchant_id": str(leg.merchant_id)},
                difference_minor=leg.goods_minor + leg.delivery_minor,
                owner="support",
            )  # fmt: skip
        suspended = {m for m in merchants if evaluate(s, m, now) == MerchantState.SUSPENDED}
        to_refund = [(leg.order_id, leg.leg_id) for leg in overdue if leg.merchant_id in suspended]
    started = 0
    for order_id, leg_id in to_refund:
        try:
            if refund_leg(rt, order_id, leg_id, key=f"merchant-suspended:{order_id}:{leg_id}"):
                started += 1
        except Exception:  # noqa: BLE001 - one refund failing must not stop the others
            import logging

            logging.getLogger(__name__).exception("refund for %s/%s failed", order_id, leg_id)
    return started


def refund_leg(rt, order_id: uuid.UUID, leg_id: str, *, key: str, reason="not_delivered") -> bool:
    """Refund what is left of one leg's value to the customer. Idempotent by key."""
    from app.orders.service import create_refund, remaining_leg_value

    with rt.sessions() as s:
        order = s.get(Order, order_id)
        leg = s.scalars(
            select(OrderLeg).where(OrderLeg.order_id == order_id, OrderLeg.leg_id == leg_id)
        ).one()
        amount = remaining_leg_value(s, order, leg)
        merchant_id = leg.merchant_id
        wallet = order.funding_source.startswith("wallet:")
    if amount <= 0:
        return False
    parties = [
        {"party_type": "merchant", "party_id": str(merchant_id), "amount_minor": amount,
         "leg_id": leg_id}
    ]  # fmt: skip
    if wallet:
        from app.wallet.orders import refund_wallet_order

        refund_wallet_order(rt, order_id=order_id, business_key=key, parties=parties)
    else:
        create_refund(rt, order_id=order_id, business_key=key, parties=parties, reason=reason)
    return True

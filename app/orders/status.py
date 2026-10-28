"""Customer-facing status projection (blueprint §5.6, §15.3).

Built only from validated records. Shows bank hold, charged, refund requested and refund
confirmed separately, and never claims more evidence than exists: a submitted void is
"hold release requested", not "released"; a provider-confirmed refund is not a bank credit.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.orders.models import DeliveryJob, Order, OrderLeg
from app.payments.models import Action, FinancialOperation, OpState, Refund, RefundState


def order_status(s: Session, order_id: uuid.UUID, account_id: uuid.UUID) -> dict[str, Any]:
    order = s.get(Order, order_id)
    if order is None or order.account_id != account_id:
        from app.errors import ErrorCode, TrollieError

        raise TrollieError(ErrorCode.NOT_FOUND, "order not found")
    ops = {
        op.action: op
        for op in s.scalars(
            select(FinancialOperation).where(
                FinancialOperation.order_id == order_id, FinancialOperation.action != Action.REFUND
            )
        )
    }
    refunds = list(s.scalars(select(Refund).where(Refund.order_id == order_id)))
    auth, capture, charge, void = (
        ops.get(a) for a in (Action.AUTHORISE, Action.CAPTURE, Action.CHARGE, Action.VOID)
    )

    def ok(op):
        return op is not None and op.state == OpState.SUCCEEDED

    bank_hold = 0
    hold_note = None
    if ok(auth) and not ok(capture):
        bank_hold = auth.amount_minor
        if void is not None:
            hold_note = (
                "hold release requested" if ok(void) else "hold release pending confirmation"
            )
    charged = capture.amount_minor if ok(capture) else (charge.amount_minor if ok(charge) else 0)
    unresolved = [
        op.action for op in ops.values() if op.state in (OpState.UNKNOWN, OpState.RECONCILING)
    ]
    legs = []
    for leg in s.scalars(
        select(OrderLeg).where(OrderLeg.order_id == order_id).order_by(OrderLeg.leg_id)
    ):
        job = s.scalars(select(DeliveryJob).where(DeliveryJob.order_leg_id == leg.id)).first()
        legs.append(
            {
                "leg_id": leg.leg_id,
                "merchant_id": str(leg.merchant_id),
                "state": leg.state,
                "delivery": job.state if job else None,
            }
        )
    return {
        "order_id": str(order.id),
        "state": order.state,
        "reason": order.attention_reason,
        "simulated": True,
        "money": {
            "currency": "ZAR",
            "bank_hold_minor": bank_hold,
            "bank_hold_note": hold_note,
            "charged_minor": charged,
            "refund_requested_minor": sum(
                r.amount_minor for r in refunds if r.state != RefundState.PROVIDER_CONFIRMED
            ),
            "refund_confirmed_minor": sum(
                r.amount_minor for r in refunds if r.state == RefundState.PROVIDER_CONFIRMED
            ),
            "refund_confirmed_note": (
                "confirmed by the payment provider; your bank may take longer to show it"
            )
            if refunds
            else None,
            "payment_status_pending_verification": bool(unresolved),
        },
        "legs": legs,
    }

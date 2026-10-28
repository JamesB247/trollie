"""Refund state sync and refund-allocation reconciliation (blueprint §14.5; T32).

Three records stay separate: the customer's entitlement (refund + ledger), what the
provider reversed from each beneficiary, and which merchant is economically liable.
"""

import uuid

from sqlalchemy.orm import Session

from app.ledger.postings import post_allocation_adjustment, post_refund_paid
from app.orders.models import Order
from app.orders.runtime import Runtime
from app.orders.state import REFUND
from app.payments.models import FinancialOperation, OpState, Refund, RefundState
from app.reconciliation.service import open_case

_MAP = {
    OpState.SUCCEEDED: RefundState.PROVIDER_CONFIRMED,
    OpState.PENDING: RefundState.PENDING,
    OpState.UNKNOWN: RefundState.UNKNOWN,
    OpState.RECONCILING: RefundState.UNKNOWN,
    OpState.FAILED_FINAL: RefundState.FAILED_REQUIRES_ACTION,
}


def sync_refund(rt: Runtime, refund_id: uuid.UUID) -> str:
    with rt.sessions() as s:
        refund = s.get(Refund, refund_id)
        op = s.get(FinancialOperation, refund.operation_id)
        need_allocation = op.state == OpState.SUCCEEDED and refund.provider_allocation is None
        op_id = op.id
    allocation = None
    if need_allocation:
        obs = rt.executor.confirm(op_id)
        allocation = list(obs.allocation) if obs is not None else None
    with rt.sessions() as s, s.begin():
        refund = s.get(Refund, refund_id, with_for_update=True)
        op = s.get(FinancialOperation, refund.operation_id)
        if refund.state == RefundState.APPROVED and op.state != OpState.CREATED:
            REFUND.move(refund, RefundState.SUBMITTED)
        target = _MAP.get(op.state)
        if target and refund.state not in (RefundState.PROVIDER_CONFIRMED, target):
            REFUND.move(refund, target)
        if refund.state == RefundState.PROVIDER_CONFIRMED:
            order = s.get(Order, refund.order_id)
            post_refund_paid(
                s,
                refund_id=refund.id,
                account_id=order.account_id,
                amount_minor=refund.amount_minor,
            )
            if allocation is not None and refund.provider_allocation is None:
                refund.provider_allocation = allocation
                _reconcile_allocation(s, refund)
        return refund.state


def _reconcile_allocation(s: Session, refund: Refund) -> None:
    """Compare what each merchant economically owes with what the provider reversed."""
    economic: dict[str, int] = {}
    for part in refund.economic_allocation:
        if part["party_type"] == "merchant":
            economic[part["party_id"]] = economic.get(part["party_id"], 0) + part["amount_minor"]
    reversed_from: dict[str, int] = {}
    for part in refund.provider_allocation or []:
        kind, _, ident = part["beneficiary"].partition(":")
        if kind == "merchant":
            reversed_from[ident] = reversed_from.get(ident, 0) + part["reversed_minor"]
    responsible = max(economic, key=economic.get) if economic else None
    for merchant_id, reversed_minor in sorted(reversed_from.items()):
        over = reversed_minor - economic.get(merchant_id, 0)
        if over <= 0 or responsible is None or merchant_id == responsible:
            continue
        # The provider took `over` from an innocent merchant's settlement.
        post_allocation_adjustment(
            s,
            refund_id=refund.id,
            merchant_id=uuid.UUID(merchant_id),
            responsible_id=uuid.UUID(responsible),
            amount_minor=over,
        )
        open_case(
            s,
            dedupe_key=f"refund-allocation:{refund.id}:{merchant_id}",
            case_type="refund_allocation_mismatch",
            refs={
                "refund_id": str(refund.id),
                "innocent_merchant": merchant_id,
                "responsible_merchant": responsible,
            },
            difference_minor=over,
        )

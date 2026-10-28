"""Wallet-funded order steps (D-W02, A2, A5). SIMULATED — NOT REAL MONEY.

Funds were reserved inside the wallet when the order was created. There is no external
payment operation at all (W16). Commitment turns held funds into obligations for the
accepted legs; anything else is released back to its source exactly once.
"""

import uuid

from sqlalchemy import select

from app.errors import ErrorCode, TrollieError
from app.merchants.adapter import MerchantTimeout
from app.orders.models import Order, OrderLeg
from app.orders.policy import decide
from app.orders.runtime import Runtime
from app.orders.service import (
    _book_deliveries,
    _commit_leg,
    _holds_valid,
    _invalidate_quote,
    _legs,
    _parties,
    _release_all,
    _set_state,
    _snapshot,
    advance,
    create_order,
    resolve_uncertain_leg,
)
from app.orders.state import LEG
from app.quotes.models import Quote
from app.wallet import service as wallet
from app.wallet.grants import authorise_under_mandate, grant_for_envelope
from app.wallet.models import Grant, MandateExecution, WalletReservation


def _grant_still_valid(rt: Runtime, order_id: uuid.UUID) -> bool:
    """W09: a mandate revoked between request and commitment stops new commitments."""
    with rt.sessions() as s:
        order = s.get(Order, order_id)
        if order.mandate_execution_id is None:
            return True
        execution = s.get(MandateExecution, order.mandate_execution_id)
        grant = s.get(Grant, execution.grant_id)
        return grant.status == "active" and rt.clock.now() < grant.valid_until


def _funds_held(rt: Runtime, order_id: uuid.UUID) -> bool:
    with rt.sessions() as s:
        res = s.scalars(
            select(WalletReservation).where(WalletReservation.order_id == order_id)
        ).one_or_none()
        return res is not None and res.state == "held"


def _cancel(rt: Runtime, order_id: uuid.UUID, reason: str) -> bool:
    _set_state(
        rt, order_id, "COMPENSATING", reason=reason, plan={"kind": "cancel_all", "reason": reason}
    )
    return True


def _payment_pending(rt: Runtime, order_id: uuid.UUID) -> bool:
    with rt.sessions() as s:
        cancel = s.get(Order, order_id).customer_cancel_requested
    if cancel:
        return _cancel(rt, order_id, "customer_cancelled")
    if not _funds_held(rt, order_id):
        return _cancel(rt, order_id, "funds_not_held")
    if not _grant_still_valid(rt, order_id):
        return _cancel(rt, order_id, "grant_revoked")
    if _holds_valid(rt, order_id):
        return _cancel(rt, order_id, "reservation_expired")
    _set_state(rt, order_id, "COMMITTING")
    return True


def _committing(rt: Runtime, order_id: uuid.UUID) -> bool:
    if not _grant_still_valid(rt, order_id):
        return _cancel(rt, order_id, "grant_revoked")
    with rt.sessions() as s:
        pending = [
            leg.id
            for leg in _legs(s, order_id)
            if leg.state in ("RESERVED", "COMMIT_REQUESTED", "UNKNOWN")
        ]
    for leg_id in pending:
        _commit_leg(rt, leg_id)
    with rt.sessions() as s:
        order = s.get(Order, order_id)
        legs = _legs(s, order_id)
        if any(leg.state in ("COMMIT_REQUESTED", "UNKNOWN") for leg in legs):
            return False  # W10: money stays held until merchant state is established
        snapshot = _snapshot(s, order)
        rejected = {leg.leg_id for leg in legs if leg.state == "REJECTED"}
        cancel = order.customer_cancel_requested
    decision = decide(snapshot, rejected)
    if cancel:
        return _cancel(rt, order_id, "customer_cancelled")
    if decision.kind == "cancel_all":
        return _cancel(rt, order_id, decision.reason)
    if not _funds_held(rt, order_id):
        return _cancel(rt, order_id, "funds_not_held")
    keep = {leg["leg_id"] for leg in snapshot["legs"]} - set(decision.removed_leg_ids)
    parties = _parties(snapshot, keep, service_fee=True)
    with rt.sessions() as s, s.begin():
        wallet.commit(s, order_id=order_id, parties=parties)
        s.get(Order, order_id, with_for_update=True).plan = {
            "kind": decision.kind,
            "reason": decision.reason,
            "removed_leg_ids": list(decision.removed_leg_ids),
        }
    _book_deliveries(rt, order_id, keep)
    _set_state(rt, order_id, "FULFILLING", reason=decision.reason if rejected else None)
    return True


def _compensating(rt: Runtime, order_id: uuid.UUID) -> bool:
    with rt.sessions() as s:
        uncertain = [
            leg.id for leg in _legs(s, order_id) if leg.state in ("COMMIT_REQUESTED", "UNKNOWN")
        ]
    if any(resolve_uncertain_leg(rt, leg_id) is None for leg_id in uncertain):
        return False  # W10: money stays held until merchant state is established
    with rt.sessions() as s:
        legs = [(leg.id, leg.state, leg.commit_ref) for leg in _legs(s, order_id)]
    for leg_id, state, commit_ref in legs:
        if state in ("ACCEPTED", "READY_FOR_COLLECTION"):
            with rt.sessions() as s, s.begin():
                LEG.move(s.get(OrderLeg, leg_id, with_for_update=True), "CANCEL_REQUESTED")
            try:
                obs = rt.merchant.cancel_order(client_ref=commit_ref)
            except MerchantTimeout:
                return False
            with rt.sessions() as s, s.begin():
                LEG.move(
                    s.get(OrderLeg, leg_id, with_for_update=True),
                    "CANCELLED" if obs.status == "cancelled" else "ACCEPTED",
                )
        elif state == "RESERVED":
            with rt.sessions() as s, s.begin():
                LEG.move(s.get(OrderLeg, leg_id, with_for_update=True), "CANCELLED")
    _release_all(rt, order_id)
    with rt.sessions() as s, s.begin():
        wallet.release(s, order_id=order_id)
    _invalidate_quote(rt, order_id)
    _set_state(rt, order_id, "CANCELLED")
    return True


def _fulfilling(rt: Runtime, order_id: uuid.UUID) -> bool:
    from app.orders.service import _fulfilling as card_fulfilling

    return card_fulfilling(rt, order_id)


WALLET_STEPS = {
    "PAYMENT_PENDING": _payment_pending,
    "COMMITTING": _committing,
    "COMPENSATING": _compensating,
    "FULFILLING": _fulfilling,
}


def execute_under_mandate(rt: Runtime, *, agent_id: uuid.UUID, quote_id: uuid.UUID) -> uuid.UUID:
    """The agent requests execution; the trusted executor decides (A2)."""
    if not rt.mandate_fixture_enabled:
        raise TrollieError(ErrorCode.CAPABILITY_NOT_ENABLED, "mandate execution is disabled")
    with rt.sessions() as s, s.begin():
        execution = authorise_under_mandate(
            s, agent_id=agent_id, quote_id=quote_id, now=rt.clock.now()
        )
        execution_id, account_id = execution.id, s.get(Quote, quote_id).account_id
    order_id = create_order(rt, account_id=account_id, mandate_execution_id=execution_id)
    advance(rt, order_id)
    return order_id


def refund_wallet_order(
    rt: Runtime, *, order_id: uuid.UUID, business_key: str, parties: list[dict]
) -> uuid.UUID:
    with rt.sessions() as s, s.begin():
        order = s.get(Order, order_id)
        envelope_id = None
        if order.funding_source.startswith("wallet:envelope:"):
            envelope_id = uuid.UUID(order.funding_source.rsplit(":", 1)[1])
        grant_active = bool(envelope_id) and grant_for_envelope(s, envelope_id) is not None
        refund = wallet.refund_to_wallet(
            s,
            order_id=order_id,
            business_key=business_key,
            parties=parties,
            grant_active=grant_active,
        )
        return refund.id

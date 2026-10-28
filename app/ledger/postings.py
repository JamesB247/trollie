"""Posting templates for each economic event (blueprint §14.3). Posting keys are derived from
the business event, so a replayed event can never post twice."""

import uuid

from sqlalchemy.orm import Session

from app.ledger import chart
from app.ledger.service import account, credit, debit, post

COURIER_NAMESPACE = uuid.UUID("a3f2c1d0-6b7e-4c3a-9e8f-1d2c3b4a5f60")


def courier_owner(code: str) -> uuid.UUID:
    return uuid.uuid5(COURIER_NAMESPACE, code)


def recipient_account(session: Session, party: dict) -> uuid.UUID:
    if party["party_type"] == "merchant":
        return account(session, chart.MERCHANT_PAYABLE, uuid.UUID(party["party_id"]))
    if party["party_type"] == "courier":
        return account(session, chart.COURIER_PAYABLE, uuid.UUID(party["party_id"]))
    return account(session, chart.PLATFORM_FEE_CLEARING, None)


def post_collection(
    session: Session, *, operation_id: uuid.UUID, amount_minor: int, parties: list[dict]
) -> uuid.UUID:
    """Provider collected `amount_minor`; allocate the obligation to each recipient."""
    clearing = account(session, chart.PROVIDER_CLEARING, None)
    legs = [debit(clearing, amount_minor)]
    legs += [
        credit(recipient_account(session, p), p["amount_minor"])
        for p in parties
        if p["amount_minor"] > 0
    ]
    return post(
        session,
        posting_key=f"collection:{operation_id}",
        event_type="collection",
        legs=legs,
        business_operation_id=operation_id,
    )


def post_refund_owed(
    session: Session, *, refund_id: uuid.UUID, account_id: uuid.UUID, parties: list[dict]
) -> uuid.UUID:
    """Customer becomes entitled to a refund; the economically responsible parties bear it."""
    owed = account(session, chart.CUSTOMER_REFUND_PAYABLE, account_id)
    total = sum(p["amount_minor"] for p in parties)
    legs = [
        debit(recipient_account(session, p), p["amount_minor"])
        for p in parties
        if p["amount_minor"] > 0
    ]
    legs.append(credit(owed, total))
    return post(
        session, posting_key=f"refund-owed:{refund_id}", event_type="refund_owed", legs=legs
    )


def post_refund_paid(
    session: Session, *, refund_id: uuid.UUID, account_id: uuid.UUID, amount_minor: int
) -> uuid.UUID:
    """The provider confirmed the refund out of collected funds (not proof of bank credit)."""
    owed = account(session, chart.CUSTOMER_REFUND_PAYABLE, account_id)
    clearing = account(session, chart.PROVIDER_CLEARING, None)
    return post(
        session,
        posting_key=f"refund-paid:{refund_id}",
        event_type="refund_paid",
        legs=[debit(owed, amount_minor), credit(clearing, amount_minor)],
    )


def post_allocation_adjustment(
    session: Session,
    *,
    refund_id: uuid.UUID,
    merchant_id: uuid.UUID,
    responsible_id: uuid.UUID,
    amount_minor: int,
) -> uuid.UUID:
    """T32: the provider reversed `amount_minor` from an innocent merchant's settlement.
    Record what the responsible merchant must repay, so the provider's over-settlement to
    it does not show as a negative payable. Paying the innocent merchant is a separate,
    case-tracked action from the operating reserve."""
    receivable = account(session, chart.REFUND_RECOVERY, responsible_id)
    responsible_payable = account(session, chart.MERCHANT_PAYABLE, responsible_id)
    return post(
        session,
        posting_key=f"refund-allocation:{refund_id}:{merchant_id}",
        event_type="refund_allocation_adjustment",
        legs=[debit(receivable, amount_minor), credit(responsible_payable, amount_minor)],
    )


def post_settlement_line(
    session: Session, *, line_ref: str, beneficiary: str, net_minor: int, fee_minor: int
) -> uuid.UUID | None:
    """Mirror a provider payout to a beneficiary and its fee out of collected funds.
    A line with nothing paid and no fee has no economic effect and posts nothing."""
    if net_minor < 0 or fee_minor < 0:
        raise ValueError("settlement amounts cannot be negative")
    if net_minor == 0 and fee_minor == 0:
        return None
    clearing = account(session, chart.PROVIDER_CLEARING, None)
    kind, _, ident = beneficiary.partition(":")
    party = {"party_type": kind, "party_id": ident or None}
    legs = []
    if net_minor:
        legs.append(debit(recipient_account(session, party), net_minor))
    if fee_minor:
        legs.append(debit(account(session, chart.PROVIDER_FEES, None), fee_minor))
    legs.append(credit(clearing, net_minor + fee_minor))
    return post(session, posting_key=f"settlement:{line_ref}", event_type="settlement", legs=legs)

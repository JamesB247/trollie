"""Reusable steps for flow tests: customers, lists, quotes, passkeys and approvals."""

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from app.accounts.crypto import AddressCipher
from app.accounts.models import CustomerAccount
from app.accounts.service import add_address_version
from app.approvals.service import (
    WebAuthnConfig,
    begin_approval,
    begin_registration,
    finish_registration,
    verify_approval,
)
from app.clock import FixedClock
from app.quotes.models import FulfilmentMode, Quote
from app.quotes.optimiser import Candidate, Quantity, Rule, Strategy
from app.quotes.service import add_item, create_session, prepare_firm_quote, request_estimates
from app.simulators.authenticator import SoftAuthenticator

CFG = WebAuthnConfig(rp_id="localhost", origin="http://localhost:8000")
CIPHER = AddressCipher.ephemeral()


@dataclass
class Customer:
    account_id: uuid.UUID
    address_id: uuid.UUID
    authenticator: SoftAuthenticator | None = None


def new_customer(db: Session, *, zone: str = "zone-a") -> Customer:
    acct = CustomerAccount(id=uuid.uuid4(), display_name="Test Household (Fictional)")
    db.add(acct)
    db.flush()
    addr = add_address_version(
        db,
        CIPHER,
        account_id=acct.id,
        label="Home",
        address_text="1 Fictional Lane",
        service_zone=zone,
    )
    db.commit()
    return Customer(acct.id, addr.id)


def register_passkey(
    db: Session,
    customer: Customer,
    clock: FixedClock,
    authenticator: SoftAuthenticator | None = None,
) -> SoftAuthenticator:
    authenticator = authenticator or SoftAuthenticator()
    challenge_id, options = begin_registration(
        db, CFG, account_id=customer.account_id, display_name="test", clock=clock
    )
    finish_registration(
        db,
        CFG,
        account_id=customer.account_id,
        challenge_id=challenge_id,
        credential=authenticator.register(options, CFG.origin),
        clock=clock,
    )
    db.commit()
    customer.authenticator = authenticator
    return authenticator


def shopping_list(
    db: Session, catalogue, customer: Customer, items: list[tuple[str, dict]], **session_kw
) -> uuid.UUID:
    """items: (product code, options) where options may set packs/measure/unit/rule/must_have."""
    shopping = create_session(
        db, account_id=customer.account_id, address_version_id=customer.address_id, **session_kw
    )
    for code, opts in items:
        quantity = (
            Quantity(measure=opts["measure"], unit=opts["unit"])
            if "measure" in opts
            else Quantity(packs=opts.get("packs", 1))
        )
        add_item(
            db,
            session_id=shopping.id,
            account_id=customer.account_id,
            line_id=code,
            rule=opts.get("rule", Rule.FLEXIBLE),
            candidates=[Candidate(catalogue[f"product:{code}"])],
            quantity=quantity,
            must_have=opts.get("must_have", False),
            source="customer",
            needs_clarification=opts.get("needs_clarification"),
        )
    db.commit()
    return shopping.id


def estimate(
    db: Session,
    customer: Customer,
    session_id: uuid.UUID,
    clock: FixedClock,
    strategy: Strategy = Strategy.CHEAPEST,
    **kw,
) -> Quote:
    result = request_estimates(
        db, session_id=session_id, account_id=customer.account_id, clock=clock, **kw
    )
    db.commit()
    quote = result.quotes[strategy]
    assert quote is not None, result.blocking
    return quote


def firm(
    sessions: sessionmaker[Session],
    merchant,
    customer: Customer,
    estimate_id: uuid.UUID,
    clock: FixedClock,
    *,
    mode: FulfilmentMode = FulfilmentMode.COMPLETE_REQUIRED,
    omissions: list[str] | None = None,
    funding: str = "pay_per_order:card_auth_capture",
):
    return prepare_firm_quote(
        sessions,
        estimate_id=estimate_id,
        account_id=customer.account_id,
        merchant=merchant,
        clock=clock,
        fulfilment_mode=mode,
        permitted_omissions=omissions or [],
        funding_source=funding,
    )


def approve(
    db: Session,
    customer: Customer,
    quote_id: uuid.UUID,
    clock: FixedClock,
    *,
    subject_type: str = "quote",
):
    challenge_id, options = begin_approval(
        db,
        CFG,
        account_id=customer.account_id,
        subject_type=subject_type,
        subject_id=quote_id,
        clock=clock,
    )
    db.commit()
    credential = customer.authenticator.assert_(options, CFG.origin)
    approval = verify_approval(
        db,
        CFG,
        account_id=customer.account_id,
        challenge_id=challenge_id,
        credential=credential,
        clock=clock,
    )
    db.commit()
    return approval

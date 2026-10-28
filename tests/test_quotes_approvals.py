"""Quotes and approvals: T02, T07, T18-T22, T49, firm-quote derivation and immutability."""

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.accounts.service import add_address_version
from app.approvals.service import begin_approval, verify_approval
from app.errors import ErrorCode, TrollieError
from app.merchants.models import Reservation, ReservationState
from app.quotes.models import FulfilmentMode, Quote, QuoteKind, QuoteState
from app.quotes.service import EXECUTION_SAFETY_MARGIN, recompute_hash
from app.simulators.faults import inject
from app.simulators.models import SimMerchantReservation
from tests.flows import (
    CFG,
    CIPHER,
    approve,
    estimate,
    firm,
    new_customer,
    register_passkey,
    shopping_list,
)
from tests.soft_authenticator import SoftAuthenticator

BASKET = [("milk-1l", {"packs": 2}), ("beans-410g", {"packs": 3}), ("tea-100", {})]


@pytest.fixture
def customer(db):
    return new_customer(db)


@pytest.fixture
def estimate_quote(db, catalogue, customer, clock):
    session_id = shopping_list(db, catalogue, customer, BASKET)
    return estimate(db, customer, session_id, clock)


def _firm_quote(sessions, merchant, customer, estimate_quote, clock, **kw):
    result = firm(sessions, merchant, customer, estimate_quote.id, clock, **kw)
    assert result.quote is not None, result.blocking
    return result.quote


# --- Estimates -----------------------------------------------------------------------


def test_t02_ambiguous_quantity_requires_clarification(db, catalogue, customer, clock):
    session_id = shopping_list(
        db,
        catalogue,
        customer,
        [("milk-1l", {"packs": 2, "needs_clarification": "2 litres or two 2-litre bottles?"})],
    )
    with pytest.raises(TrollieError) as err:
        estimate(db, customer, session_id, clock)
    assert err.value.code is ErrorCode.VALIDATION_FAILED and err.value.details["line_ids"] == [
        "milk-1l"
    ]
    db.rollback()


def test_estimate_snapshot_is_hashed_immutable_and_not_approvable(
    db, customer, estimate_quote, clock
):
    assert estimate_quote.kind == QuoteKind.ESTIMATE and estimate_quote.state == QuoteState.ESTIMATE
    assert recompute_hash(estimate_quote) == estimate_quote.quote_hash
    snap = estimate_quote.snapshot
    assert snap["simulated"] is True and snap["currency"] == "ZAR"
    assert snap["total_minor"] == snap["goods_minor"] + snap["delivery_minor"] + 2000
    assert all(leg["seller"]["legal_name"] for leg in snap["legs"])
    with pytest.raises(DBAPIError, match="immutable"):
        db.execute(
            text("UPDATE quotes SET total_minor = 1 WHERE id = :q"), {"q": estimate_quote.id}
        )
    db.rollback()
    register_passkey(db, customer, clock)
    with pytest.raises(TrollieError, match="estimate cannot be approved"):
        begin_approval(
            db,
            CFG,
            account_id=customer.account_id,
            subject_type="quote",
            subject_id=estimate_quote.id,
            clock=clock,
        )
    db.rollback()


# --- Firm quotes ---------------------------------------------------------------------


def test_firm_quote_requires_holds_and_derives_from_estimate(
    db, sessions, merchant, customer, estimate_quote, clock
):
    quote = _firm_quote(sessions, merchant, customer, estimate_quote, clock)
    db.expire_all()
    assert quote.kind == QuoteKind.FIRM and quote.state == QuoteState.FIRM
    assert db.get(Quote, estimate_quote.id).state == QuoteState.REPLACED
    legs = quote.snapshot["legs"]
    assert [leg["lines"] for leg in legs] == [
        leg["lines"] for leg in estimate_quote.snapshot["legs"]
    ]
    reservations = [db.get(Reservation, uuid.UUID(leg["reservation"]["id"])) for leg in legs]
    assert all(r.state == ReservationState.HELD for r in reservations)
    assert quote.expires_at <= min(r.expires_at for r in reservations) - EXECUTION_SAFETY_MARGIN
    assert quote.snapshot["fulfilment_policy"]["mode"] == "complete_required"
    assert quote.snapshot["funding_source"] == "pay_per_order:card_auth_capture"


def test_t07_no_hold_means_no_firm_quote_and_other_holds_released(
    db, sessions, merchant, customer, estimate_quote, clock
):
    legs = estimate_quote.snapshot["legs"]
    target = legs[-1]["location_id"]
    inject(db, system="merchant", target=target, operation="prepare_reservation", mode="reject")
    db.commit()
    result = firm(sessions, merchant, customer, estimate_quote.id, clock)
    assert result.quote is None and result.blocking[0].kind == "reservation_not_held"
    db.expire_all()
    assert db.get(Quote, estimate_quote.id).state == QuoteState.ESTIMATE
    for res in db.scalars(
        select(Reservation)
        .where(Reservation.created_at.is_not(None))
        .order_by(Reservation.created_at.desc())
        .limit(len(legs))
    ):
        assert res.state in (ReservationState.REJECTED, ReservationState.RELEASED)
        sim = db.get(SimMerchantReservation, res.client_ref)
        assert sim is None or sim.state == "released"


def test_reservation_timeout_after_effect_resolved_by_lookup(
    db, sessions, merchant, customer, estimate_quote, clock
):
    target = estimate_quote.snapshot["legs"][0]["location_id"]
    inject(
        db,
        system="merchant",
        target=target,
        operation="prepare_reservation",
        mode="timeout_after_effect",
    )
    db.commit()
    quote = _firm_quote(sessions, merchant, customer, estimate_quote, clock)
    res_id = uuid.UUID(quote.snapshot["legs"][0]["reservation"]["id"])
    res = db.get(Reservation, res_id)
    assert res.state == ReservationState.HELD and res.evidence["note"] == "timeout_then_lookup"
    # Exactly one hold exists at the merchant for that reference: no duplicate reservation.
    assert (
        db.scalar(
            select(SimMerchantReservation).where(
                SimMerchantReservation.client_ref == res.client_ref
            )
        ).state
        == "held"
    )


def test_complete_required_rejects_permitted_omissions(
    sessions, merchant, customer, estimate_quote, clock
):
    with pytest.raises(TrollieError, match="cannot permit omissions"):
        firm(sessions, merchant, customer, estimate_quote.id, clock, omissions=["tea-100"])


def test_must_have_cannot_be_a_permitted_omission(
    db, sessions, merchant, catalogue, customer, clock
):
    session_id = shopping_list(
        db, catalogue, customer, [("milk-1l", {"must_have": True}), ("tea-100", {})]
    )
    est = estimate(db, customer, session_id, clock)
    with pytest.raises(TrollieError, match="must-have"):
        firm(
            sessions,
            merchant,
            customer,
            est.id,
            clock,
            mode=FulfilmentMode.ALLOW_PARTIAL,
            omissions=["milk-1l"],
        )


# --- Approvals -----------------------------------------------------------------------


def test_approval_binds_to_firm_quote(db, sessions, merchant, customer, estimate_quote, clock):
    quote = _firm_quote(sessions, merchant, customer, estimate_quote, clock)
    register_passkey(db, customer, clock)
    approval = approve(db, customer, quote.id, clock)
    db.expire_all()
    assert approval.subject_hash == quote.quote_hash and approval.user_verified
    assert db.get(Quote, quote.id).state == QuoteState.APPROVED


def _challenge(db, customer, quote, clock):
    challenge_id, options = begin_approval(
        db,
        CFG,
        account_id=customer.account_id,
        subject_type="quote",
        subject_id=quote.id,
        clock=clock,
    )
    db.commit()
    return challenge_id, options


def _rejected(db, customer, challenge_id, credential, clock, reason):
    with pytest.raises(TrollieError) as err:
        verify_approval(
            db,
            CFG,
            account_id=customer.account_id,
            challenge_id=challenge_id,
            credential=credential,
            clock=clock,
        )
    db.rollback()
    assert reason in str(err.value.details.get("reason", err.value.message))


def test_t20_replayed_assertion_rejected(db, sessions, merchant, customer, estimate_quote, clock):
    quote = _firm_quote(sessions, merchant, customer, estimate_quote, clock)
    register_passkey(db, customer, clock)
    challenge_id, options = _challenge(db, customer, quote, clock)
    credential = customer.authenticator.assert_(options, CFG.origin)
    verify_approval(
        db,
        CFG,
        account_id=customer.account_id,
        challenge_id=challenge_id,
        credential=credential,
        clock=clock,
    )
    db.commit()
    _rejected(db, customer, challenge_id, credential, clock, "challenge_already_used")


def test_t21_wrong_origin_account_or_credential_rejected(
    db, sessions, merchant, catalogue, customer, estimate_quote, clock
):
    quote = _firm_quote(sessions, merchant, customer, estimate_quote, clock)
    register_passkey(db, customer, clock)
    other = new_customer(db)
    register_passkey(db, other, clock)

    challenge_id, options = _challenge(db, customer, quote, clock)
    evil_origin = customer.authenticator.assert_(options, "https://evil.example")
    _rejected(db, customer, challenge_id, evil_origin, clock, "assertion_failed")
    wrong_rp = customer.authenticator.assert_(options, CFG.origin, rp_id="evil.example")
    _rejected(db, customer, challenge_id, wrong_rp, clock, "assertion_failed")
    # The other customer's valid passkey cannot approve this customer's quote.
    others_credential = other.authenticator.assert_(options, CFG.origin)
    _rejected(db, customer, challenge_id, others_credential, clock, "credential_not_allowed")
    # Nor can the other account use this account's challenge at all.
    with pytest.raises(TrollieError):
        verify_approval(
            db,
            CFG,
            account_id=other.account_id,
            challenge_id=challenge_id,
            credential=others_credential,
            clock=clock,
        )
    db.rollback()
    # A signature over a different challenge fails.
    forged = customer.authenticator.assert_(options, CFG.origin, challenge="AAAA")
    _rejected(db, customer, challenge_id, forged, clock, "assertion_failed")


def test_t22_user_verification_required_but_not_biometric(
    db, sessions, merchant, customer, estimate_quote, clock
):
    """A PIN-verifying authenticator (UV flag set, no biometrics) passes; an authenticator
    without user verification is refused. No biometric data is ever received."""
    quote = _firm_quote(sessions, merchant, customer, estimate_quote, clock)
    no_uv = SoftAuthenticator(user_verifying=False)
    with pytest.raises(TrollieError, match="approval rejected"):
        register_passkey(db, customer, clock, authenticator=no_uv)
    db.rollback()
    register_passkey(db, customer, clock, authenticator=SoftAuthenticator(user_verifying=True))
    approve(db, customer, quote.id, clock)


def test_expired_quote_cannot_be_approved(db, sessions, merchant, customer, estimate_quote, clock):
    quote = _firm_quote(sessions, merchant, customer, estimate_quote, clock)
    register_passkey(db, customer, clock)
    challenge_id, options = _challenge(db, customer, quote, clock)
    clock.advance(seconds=(quote.expires_at - clock.now()).total_seconds() + 1)
    credential = customer.authenticator.assert_(options, CFG.origin)
    with pytest.raises(TrollieError) as err:
        verify_approval(
            db,
            CFG,
            account_id=customer.account_id,
            challenge_id=challenge_id,
            credential=credential,
            clock=clock,
        )
    assert err.value.code in (ErrorCode.APPROVAL_INVALID, ErrorCode.QUOTE_EXPIRED)
    db.rollback()


def test_t19_approved_address_version_survives_later_edit(
    db, sessions, merchant, customer, estimate_quote, clock
):
    quote = _firm_quote(sessions, merchant, customer, estimate_quote, clock)
    register_passkey(db, customer, clock)
    approve(db, customer, quote.id, clock)
    newer = add_address_version(
        db,
        CIPHER,
        account_id=customer.account_id,
        label="Home",
        address_text="99 Different Road",
        service_zone="zone-a",
    )
    db.commit()
    destination = db.get(Quote, quote.id).snapshot["destination"]
    assert destination["address_version_id"] == str(customer.address_id)
    assert destination["version"] == 1 and newer.version == 2


def test_t49_other_account_cannot_see_or_approve_quote(
    db, sessions, merchant, customer, estimate_quote, clock
):
    quote = _firm_quote(sessions, merchant, customer, estimate_quote, clock)
    other = new_customer(db)
    register_passkey(db, other, clock)
    with pytest.raises(TrollieError) as err:
        begin_approval(
            db,
            CFG,
            account_id=other.account_id,
            subject_type="quote",
            subject_id=quote.id,
            clock=clock,
        )
    assert err.value.code is ErrorCode.NOT_FOUND
    db.rollback()

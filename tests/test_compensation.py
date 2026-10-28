"""Failure handling and the compensation matrix (blueprint §9.5): T05, T06, T08-T10, T18,
T24, T26, T28, T30, T31, T37-T40, T42."""

import threading
import uuid

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.approvals.models import Approval, ApprovalChallenge
from app.controls.models import Incident
from app.durable.models import InboxEvent
from app.errors import ErrorCode, TrollieError
from app.ledger.models import LedgerTransaction
from app.merchants.models import Reservation, ReservationState
from app.orders.handlers import pump
from app.orders.models import DeliveryJob, Order, OrderLeg
from app.orders.service import create_order, redirect_delivery, request_cancellation
from app.orders.status import order_status
from app.payments.models import FinancialOperation, OpState, Refund
from app.quotes.models import FulfilmentMode
from app.reconciliation.models import ReconciliationCase
from app.simulators.faults import inject
from app.simulators.models import SimCourierBooking, SimPayment
from tests.order_support import approved, pay, purchase

CARD = "pay_per_order:card_auth_capture"
INSTANT = "pay_per_order:immediate"
PARTIAL = FulfilmentMode.ALLOW_PARTIAL


def fault(db, system, target, operation, mode, times=1):
    inject(db, system=system, target=str(target), operation=operation, mode=mode, times=times)
    db.commit()


def ops(db, order_id):
    db.expire_all()
    return {
        op.action: op
        for op in db.scalars(
            select(FinancialOperation).where(FinancialOperation.order_id == order_id)
        )
    }


def legs(db, order_id):
    return {
        leg.leg_id: leg for leg in db.scalars(select(OrderLeg).where(OrderLeg.order_id == order_id))
    }


def order(db, order_id):
    db.expire_all()
    return db.get(Order, order_id)


def cases(db, case_type, needle):
    return [
        c
        for c in db.scalars(
            select(ReconciliationCase).where(ReconciliationCase.case_type == case_type)
        )
        if needle in str(c.refs)
    ]


# --- Merchant failures ---------------------------------------------------------------


def test_t37_basket_fails_before_capture_voids_and_releases(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=CARD)
    fault(db, "merchant", split_world["location:b"], "commit_order", "reject")
    pay(rt, p.checkout_ref)
    o = order(db, p.order_id)
    assert o.state == "CANCELLED" and o.plan["reason"] == "complete_required"
    money = ops(db, p.order_id)
    assert "capture" not in money and money["void"].state == OpState.SUCCEEDED
    assert {k: v.state for k, v in legs(db, p.order_id).items()} == {
        "leg_1": "CANCELLED",
        "leg_2": "REJECTED",
    }
    status = order_status(db, p.order_id, p.customer.account_id)["money"]
    # A submitted void is a requested release, not proof the bank has released the hold.
    assert status["charged_minor"] == 0 and status["bank_hold_note"] == "hold release requested"


def test_t05_must_have_overrides_allow_partial(rt, db, split_world):
    items = [("a-rice", {}), ("b-tea", {"must_have": True}), ("b-jam", {})]
    p = purchase(rt, db, split_world, funding=CARD, items=items, mode=PARTIAL, omissions=["b-jam"])
    fault(db, "merchant", split_world["location:b"], "commit_order", "reject")
    pay(rt, p.checkout_ref)
    o = order(db, p.order_id)
    assert o.state == "CANCELLED" and o.plan["reason"] == "must_have_unavailable"
    assert "capture" not in ops(db, p.order_id)


def test_t06_permitted_omission_removes_only_that_leg(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=CARD, mode=PARTIAL, omissions=["b-tea"])
    fault(db, "merchant", split_world["location:b"], "commit_order", "reject")
    pay(rt, p.checkout_ref)
    o = order(db, p.order_id)
    assert o.state == "FULFILLING" and o.plan["removed_leg_ids"] == ["leg_2"]
    leg_b = next(leg for leg in p.quote.snapshot["legs"] if leg["leg_id"] == "leg_2")
    expected = p.quote.total_minor - leg_b["goods_minor"] - leg_b["delivery"]["fee_minor"]
    money = ops(db, p.order_id)
    assert money["capture"].amount_minor == expected  # nothing added with the freed money
    assert money["capture"].amount_minor < money["authorise"].amount_minor
    from tests.test_orders import _deliver_all

    _deliver_all(rt, db, p.order_id)
    assert order(db, p.order_id).state == "PARTIAL"


def test_omission_not_permitted_cancels_everything(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=CARD, mode=PARTIAL, omissions=["a-oil"])
    fault(db, "merchant", split_world["location:b"], "commit_order", "reject")
    pay(rt, p.checkout_ref)
    assert order(db, p.order_id).plan["reason"] == "omission_not_permitted"


def test_t38_immediate_one_leg_fails_after_other_committed(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=INSTANT)
    fault(db, "merchant", split_world["location:b"], "commit_order", "reject")
    pay(rt, p.checkout_ref)
    o = order(db, p.order_id)
    assert o.state == "CANCELLED"
    refund = db.scalars(select(Refund).where(Refund.order_id == p.order_id)).one()
    assert refund.amount_minor == p.quote.total_minor
    status = order_status(db, p.order_id, p.customer.account_id)
    assert {leg["leg_id"]: leg["state"] for leg in status["legs"]} == {
        "leg_1": "CANCELLED",
        "leg_2": "REJECTED",
    }
    money = status["money"]
    assert money["charged_minor"] == p.quote.total_minor
    assert money["refund_requested_minor"] + money["refund_confirmed_minor"] == p.quote.total_minor


def test_immediate_permitted_omission_refunds_only_failed_leg(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=INSTANT, mode=PARTIAL, omissions=["b-tea"])
    fault(db, "merchant", split_world["location:b"], "commit_order", "reject")
    pay(rt, p.checkout_ref)
    assert order(db, p.order_id).state == "FULFILLING"
    refund = db.scalars(select(Refund).where(Refund.order_id == p.order_id)).one()
    leg_b = next(leg for leg in p.quote.snapshot["legs"] if leg["leg_id"] == "leg_2")
    assert refund.amount_minor == leg_b["goods_minor"] + leg_b["delivery"]["fee_minor"]


def test_t10_merchant_loses_reserved_stock(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=CARD)
    fault(db, "merchant", split_world["location:a"], "commit_order", "lose_stock")
    pay(rt, p.checkout_ref)
    assert order(db, p.order_id).state == "CANCELLED"
    leg_a = legs(db, p.order_id)["leg_1"]
    assert leg_a.state == "REJECTED" and leg_a.evidence["reason"] == "stock_lost"
    assert any(
        str(leg_a.id) in str(i.details)
        for i in db.scalars(
            select(Incident).where(Incident.kind == "merchant_reservation_unreliable")
        )
    )


def test_merchant_commit_timeout_resolved_by_lookup(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=CARD)
    fault(db, "merchant", split_world["location:a"], "commit_order", "timeout_after_effect")
    pay(rt, p.checkout_ref)
    assert order(db, p.order_id).state == "FULFILLING"
    assert legs(db, p.order_id)["leg_1"].state == "ACCEPTED"


# --- Holds and timing ----------------------------------------------------------------


def test_t08_reservation_expires_during_3ds(rt, db, split_world, clock):
    p = purchase(rt, db, split_world, funding=CARD)
    clock.advance(minutes=31)  # the 30-minute hold lapses while the customer is in 3DS
    pay(rt, p.checkout_ref)
    o = order(db, p.order_id)
    assert o.state == "CANCELLED" and o.attention_reason == "reservation_expired"
    assert ops(db, p.order_id)["void"].state == OpState.SUCCEEDED
    assert all(leg.state != "ACCEPTED" for leg in legs(db, p.order_id).values())


def test_t09_immediate_payment_after_expiry_resecures_supply(rt, db, split_world, clock):
    p = purchase(rt, db, split_world, funding=INSTANT)
    clock.advance(minutes=31)
    pay(rt, p.checkout_ref)
    o = order(db, p.order_id)
    assert o.state == "FULFILLING" and o.attention_reason == "supply_resecured"
    assert all("resecured_reservation" in leg.evidence for leg in legs(db, p.order_id).values())


def test_t09_immediate_payment_after_expiry_refunds_when_supply_gone(rt, db, split_world, clock):
    p = purchase(rt, db, split_world, funding=INSTANT)
    clock.advance(minutes=31)
    fault(db, "merchant", split_world["location:a"], "prepare_reservation", "reject")
    pay(rt, p.checkout_ref)
    o = order(db, p.order_id)
    assert o.state == "CANCELLED"
    refund = db.scalars(select(Refund).where(Refund.order_id == p.order_id)).one()
    assert refund.amount_minor == p.quote.total_minor


# --- Authority -----------------------------------------------------------------------


def test_t18_quote_cannot_change_and_mismatched_approval_rejected(rt, db, split_world):
    customer, quote, approval = approved(rt, db, split_world)
    with pytest.raises(DBAPIError, match="immutable"):
        db.execute(
            text(
                "UPDATE quotes SET maximum_payable_minor = maximum_payable_minor + 1 WHERE id = :q"
            ),
            {"q": quote.id},
        )
    db.rollback()
    challenge = ApprovalChallenge(
        account_id=customer.account_id,
        subject_type="quote",
        subject_id=quote.id,
        subject_hash="tampered",
        challenge=uuid.uuid4().bytes,
        rp_id="localhost",
        origin="http://localhost:8000",
        expires_at=rt.clock.now(),
    )
    db.add(challenge)
    db.flush()
    forged = Approval(
        challenge_id=challenge.id,
        account_id=customer.account_id,
        subject_type="quote",
        subject_id=quote.id,
        subject_hash="tampered",
        credential_id=db.get(Approval, approval.id).credential_id,
        user_verified=True,
        sign_count=99,
        authenticator_data_sha256="x",
    )
    db.add(forged)
    db.commit()
    with pytest.raises(TrollieError) as err:
        create_order(rt, account_id=customer.account_id, approval_id=forged.id)
    assert err.value.code is ErrorCode.REAPPROVAL_REQUIRED


def test_expired_quote_cannot_start_execution(rt, db, split_world, clock):
    customer, quote, approval = approved(rt, db, split_world)
    clock.advance(seconds=(quote.expires_at - clock.now()).total_seconds() + 1)
    with pytest.raises(TrollieError) as err:
        create_order(rt, account_id=customer.account_id, approval_id=approval.id)
    assert err.value.code is ErrorCode.QUOTE_EXPIRED


def test_t24_parallel_orders_from_one_approval_execute_once(rt, db, split_world):
    customer, quote, approval = approved(rt, db, split_world)
    results: list[uuid.UUID] = []
    errors: list[Exception] = []
    barrier = threading.Barrier(4)

    def go():
        barrier.wait()
        try:
            results.append(
                create_order(rt, account_id=customer.account_id, approval_id=approval.id)
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=go) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors and len(set(results)) == 1
    assert (
        db.scalar(select(func.count()).select_from(Order).where(Order.approval_id == approval.id))
        == 1
    )
    assert (
        db.scalar(
            select(func.count())
            .select_from(FinancialOperation)
            .where(FinancialOperation.order_id == results[0])
        )
        == 1
    )


def test_t31_single_destination_profile_rejects_before_any_call(rt, db, split_world):
    customer, quote, approval = approved(rt, db, split_world)
    rt.profile_override = "simpay-restricted"
    with pytest.raises(TrollieError) as err:
        create_order(rt, account_id=customer.account_id, approval_id=approval.id)
    assert err.value.code is ErrorCode.CAPABILITY_NOT_ENABLED
    assert (
        db.scalar(select(func.count()).select_from(Order).where(Order.approval_id == approval.id))
        == 0
    )


# --- Provider ambiguity --------------------------------------------------------------


def test_t26_timeouts_after_provider_accepted_never_duplicate(rt, db, split_world):
    fault(db, "payment", "create_checkout", "create_checkout", "timeout_after_effect")
    p = purchase(rt, db, split_world, funding=CARD)
    assert p.checkout_ref is not None  # recovered by lookup with the same key
    collect = ops(db, p.order_id)["authorise"]
    assert (
        db.scalar(select(func.count()).where(SimPayment.client_key == collect.idempotency_key)) == 1
    )
    fault(db, "payment", "capture", "capture", "timeout_after_effect")
    pay(rt, p.checkout_ref)
    capture = ops(db, p.order_id)["capture"]
    assert order(db, p.order_id).state == "FULFILLING"
    assert capture.state == OpState.SUCCEEDED
    assert (
        db.scalar(select(func.count()).where(SimPayment.client_key == capture.idempotency_key)) == 1
    )


def test_t28_duplicate_webhook_has_one_effect(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=CARD)
    fault(db, "payment", "customer_completes", "customer_completes", "duplicate_webhook")
    pay(rt, p.checkout_ref)
    capture = ops(db, p.order_id)["capture"]
    assert order(db, p.order_id).state == "FULFILLING"
    assert (
        db.scalar(
            select(func.count())
            .select_from(LedgerTransaction)
            .where(LedgerTransaction.posting_key == f"collection:{capture.id}")
        )
        == 1
    )
    auth_events = [
        e
        for e in db.scalars(select(InboxEvent).where(InboxEvent.event_type == "payment.authorised"))
        if e.payload.get("reference") == f"order-{p.order_id}"
    ]
    assert len(auth_events) == 1


def test_t30_callback_success_but_lookup_conflicts(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=CARD)
    fault(db, "payment", "query", "query", "conflicting_lookup")
    pay(rt, p.checkout_ref)
    o = order(db, p.order_id)
    assert o.state == "NEEDS_ATTENTION" and o.attention_reason == "payment_evidence_conflict"
    assert {leg.state for leg in legs(db, p.order_id).values()} == {"RESERVED"}  # no dispatch
    assert cases(db, "callback_lookup_conflict", str(ops(db, p.order_id)["authorise"].id))


def test_t39_cancellation_races_capture(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=CARD)
    # The capture lands but both its response and its webhook are lost.
    fault(db, "payment", "capture", "capture", "timeout_after_effect+drop_webhook")
    fault(db, "payment", "query", "query", "pass")  # the pre-commit confirmation succeeds
    fault(db, "payment", "query", "query", "timeout_before_effect", times=50)
    pay(rt, p.checkout_ref)
    assert ops(db, p.order_id)["capture"].state in (OpState.UNKNOWN, OpState.RECONCILING)
    db.execute(text("DELETE FROM sim_faults"))  # the provider becomes reachable again
    db.commit()
    request_cancellation(rt, account_id=p.customer.account_id, order_id=p.order_id)
    pump(rt, rt.payments)
    o = order(db, p.order_id)
    money = ops(db, p.order_id)
    assert money["capture"].state == OpState.SUCCEEDED and "void" not in money
    assert o.state == "CANCELLED"
    refund = db.scalars(select(Refund).where(Refund.order_id == p.order_id)).one()
    assert refund.amount_minor == money["capture"].amount_minor  # no lost obligation


def test_cancel_during_checkout_waits_for_observed_result(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=CARD)
    request_cancellation(rt, account_id=p.customer.account_id, order_id=p.order_id)
    assert order(db, p.order_id).state == "PAYMENT_PENDING"  # live attempt not abandoned
    pay(rt, p.checkout_ref)
    o = order(db, p.order_id)
    assert o.state == "CANCELLED" and ops(db, p.order_id)["void"].state == OpState.SUCCEEDED


# --- Delivery ------------------------------------------------------------------------


def test_t40_courier_booking_timeout_looks_up_not_rebooks(rt, db, split_world):
    fault(db, "courier", "book", "book", "timeout_after_effect")
    p = purchase(rt, db, split_world, funding=CARD)
    pay(rt, p.checkout_ref)
    jobs = [
        db.scalars(select(DeliveryJob).where(DeliveryJob.order_leg_id == leg.id)).one()
        for leg in legs(db, p.order_id).values()
    ]
    assert {j.state for j in jobs} == {"BOOKED"}
    for j in jobs:
        assert (
            db.scalar(select(func.count()).where(SimCourierBooking.booking_ref == j.booking_ref))
            == 1
        )


def test_t42_delivery_to_unapproved_address_rejected(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=CARD)
    pay(rt, p.checkout_ref)
    job = db.scalars(
        select(DeliveryJob)
        .join(OrderLeg, OrderLeg.id == DeliveryJob.order_leg_id)
        .where(OrderLeg.order_id == p.order_id)
    ).first()
    assert job.address_version_id == p.customer.address_id
    with pytest.raises(TrollieError) as err:
        redirect_delivery(
            rt, job_id=job.id, address_version_id=uuid.uuid4(), requested_by="courier:driver-7"
        )
    assert err.value.code is ErrorCode.REAPPROVAL_REQUIRED
    db.expire_all()
    assert db.get(DeliveryJob, job.id).address_version_id == p.customer.address_id


def test_reservations_released_after_cancellation(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=CARD)
    pay(rt, p.checkout_ref, approve=False)
    for leg in legs(db, p.order_id).values():
        assert db.get(Reservation, leg.reservation_id).state == ReservationState.RELEASED


def test_only_one_worker_advances_an_order_at_a_time(rt, db, split_world):
    """While another worker holds the order's lock, advance() is a no-op; once released, the
    order proceeds. Prevents interleaved steps acting on stale state."""
    from app.orders.service import _lock_key, advance

    p = purchase(rt, db, split_world, funding=CARD)
    rt.payments.customer_completes(p.checkout_ref)
    with rt.sessions() as holder:
        holder.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _lock_key(p.order_id)})
        pump(rt, rt.payments)  # webhook processed, but the order cannot be advanced
        assert order(db, p.order_id).state == "PAYMENT_PENDING"
        holder.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _lock_key(p.order_id)})
        holder.commit()
    advance(rt, p.order_id)
    assert order(db, p.order_id).state == "FULFILLING"

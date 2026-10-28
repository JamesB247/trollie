"""Refunds, settlement and provider ambiguity: T27, T32-T34, T36, T51, T53, T54, plus a
property test over every state machine."""

import threading
import uuid

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import func, select, text

from app.errors import TrollieError
from app.ledger import chart
from app.ledger.service import account, balance
from app.orders.handlers import pump
from app.orders.service import create_refund
from app.orders.state import MACHINES
from app.payments.models import Action, FinancialOperation, OpState, Refund, RefundState
from app.payments.operations import create_operation
from app.payments.profiles import PROFILES
from app.payments.settlement import import_settlement
from app.reconciliation.models import ReconciliationCase
from app.simulators.faults import inject
from app.simulators.models import SimPayment
from tests.order_support import pay, purchase
from tests.test_compensation import fault, ops

CARD = "pay_per_order:card_auth_capture"


@pytest.fixture
def paid_order(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=CARD)
    pay(rt, p.checkout_ref)
    return p


def _merchant_part(p, leg_id, amount):
    leg = next(leg for leg in p.quote.snapshot["legs"] if leg["leg_id"] == leg_id)
    return [
        {
            "party_type": "merchant",
            "party_id": leg["seller"]["merchant_id"],
            "amount_minor": amount,
            "leg_id": leg_id,
        }
    ]


def _cases(db, case_type, needle):
    return [
        c
        for c in db.scalars(
            select(ReconciliationCase).where(ReconciliationCase.case_type == case_type)
        )
        if needle in str(c.refs)
    ]


# --- Refunds -------------------------------------------------------------------------


def test_t33_concurrent_partial_refunds_cannot_exceed_entitlement(rt, db, paid_order):
    captured = ops(db, paid_order.order_id)["capture"].amount_minor
    share = captured * 6 // 10
    outcomes: list[str] = []
    barrier = threading.Barrier(2)

    def go(n):
        barrier.wait()
        try:
            create_refund(
                rt,
                order_id=paid_order.order_id,
                business_key=f"race:{uuid.uuid4()}",
                parties=_merchant_part(paid_order, "leg_1", share),
                reason="race",
            )
            outcomes.append("ok")
        except TrollieError:
            outcomes.append("refused")

    threads = [threading.Thread(target=go, args=(n,)) for n in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == ["ok", "refused"]
    total = db.scalar(
        select(func.sum(Refund.amount_minor)).where(Refund.order_id == paid_order.order_id)
    )
    assert total <= captured


def test_t34_refund_timeout_then_user_retry_is_the_same_refund(rt, db, paid_order):
    fault(db, "payment", "refund", "refund", "timeout_after_effect+drop_webhook")
    fault(db, "payment", "query", "query", "timeout_before_effect")
    key = f"issue:{uuid.uuid4()}"
    parts = _merchant_part(paid_order, "leg_1", 1000)
    first = create_refund(
        rt, order_id=paid_order.order_id, business_key=key, parties=parts, reason="damaged"
    )
    assert db.get(Refund, first).state == RefundState.UNKNOWN
    retry = create_refund(
        rt, order_id=paid_order.order_id, business_key=key, parties=parts, reason="damaged"
    )
    assert retry == first
    pump(rt, rt.payments)  # reconciliation resolves the original by lookup
    db.expire_all()
    refund = db.get(Refund, first)
    assert refund.state == RefundState.PROVIDER_CONFIRMED
    op = db.get(FinancialOperation, refund.operation_id)
    assert db.scalar(select(func.count()).where(SimPayment.client_key == op.idempotency_key)) == 1
    with pytest.raises(TrollieError, match="different amount"):
        create_refund(
            rt,
            order_id=paid_order.order_id,
            business_key=key,
            parties=_merchant_part(paid_order, "leg_1", 2000),
            reason="damaged",
        )


def test_t32_retailer_specific_refund_on_proportional_split(rt, db, paid_order):
    """A refund caused only by store B is reversed proportionally by the provider. Trollie
    records B's liability and opens a case so store A does not bear B's cost."""
    leg_b = next(leg for leg in paid_order.quote.snapshot["legs"] if leg["leg_id"] == "leg_2")
    b_id = uuid.UUID(leg_b["seller"]["merchant_id"])
    receivable = account(db, chart.REFUND_RECOVERY, b_id)
    before = balance(db, receivable)
    db.commit()
    refund_id = create_refund(
        rt,
        order_id=paid_order.order_id,
        business_key=f"b-only:{uuid.uuid4()}",
        parties=_merchant_part(paid_order, "leg_2", leg_b["goods_minor"]),
        reason="store_b_missing_item",
    )
    pump(rt, rt.payments)
    db.expire_all()
    refund = db.get(Refund, refund_id)
    assert refund.state == RefundState.PROVIDER_CONFIRMED and refund.provider_allocation
    reversed_from_a = sum(
        part["reversed_minor"]
        for part in refund.provider_allocation
        if part["beneficiary"] != f"merchant:{b_id}" and part["beneficiary"].startswith("merchant:")
    )
    assert reversed_from_a > 0  # the provider did take some of A's share
    case = _cases(db, "refund_allocation_mismatch", str(refund_id))
    assert len(case) == 1 and case[0].difference_minor == reversed_from_a
    assert balance(db, receivable) - before == reversed_from_a


# --- Settlement ----------------------------------------------------------------------


def test_t53_t36_t54_settlement_import(rt, db, paid_order):
    capture = ops(db, paid_order.order_id)["capture"]
    inject(db, system="payment", target="settlement", operation="payout", mode="payout_failed")
    db.commit()
    report = rt.payments.settlement_report(f"rpt-{uuid.uuid4()}")
    ours = [ln for ln in report["lines"] if ln["operation_ref"] == capture.external_ref]
    assert ours and sum(ln["gross_minor"] for ln in ours) == capture.amount_minor
    assert import_settlement(rt, report) == "imported"
    assert import_settlement(rt, report) == "duplicate"  # T53
    # The same provider lines re-sent under another report reference are not posted again.
    clearing = account(db, chart.PROVIDER_CLEARING, None)
    before = balance(db, clearing)
    db.rollback()
    assert import_settlement(rt, {**report, "report_ref": report["report_ref"] + "-resent"}) == (
        "imported"
    )
    assert balance(db, clearing) == before
    # T36: a failed payout keeps the payable open and is owned by a case.
    failed = [ln for ln in report["lines"] if ln["kind"] == "payout_failed"]
    assert failed and _cases(db, "payout_failed", failed[0]["line_ref"])


def test_t54_unexplained_difference_is_an_owned_case_not_an_entry(rt, db, paid_order):
    capture = ops(db, paid_order.order_id)["capture"]
    report = rt.payments.settlement_report(f"rpt-{uuid.uuid4()}")
    for ln in report["lines"]:
        ln["line_ref"] += "-x"
        if (
            ln["operation_ref"] == capture.external_ref
            and ln["beneficiary"] == "platform"
            and ln["kind"] == "payout"
        ):
            ln["gross_minor"] -= 137  # an unexplained shortfall in the provider's report
            ln["net_minor"] -= 137
    postings_before = db.scalar(
        text("SELECT count(*) FROM ledger_transactions WHERE event_type NOT IN ('settlement')")
    )
    import_settlement(rt, report)
    case = _cases(db, "settlement_discrepancy", str(capture.id))
    assert len(case) == 1 and case[0].difference_minor == -137 and case[0].owner == "finance-ops"
    assert (
        db.scalar(
            text("SELECT count(*) FROM ledger_transactions WHERE event_type NOT IN ('settlement')")
        )
        == postings_before
    )


# --- Provider ambiguity at the executor level ---------------------------------------


def _standalone_charge(rt, db, amount=5000):
    profile = PROFILES["simpay-instant"]
    op = create_operation(
        db,
        order_id=None,
        action=Action.CHARGE,
        profile=profile,
        amount_minor=amount,
        idempotency_key=f"test-charge:{uuid.uuid4()}",
        request={},
        subject_type="test",
    )
    db.commit()
    return op


ARGS = {"collection": "immediate", "reference": "test", "beneficiaries": []}


def test_t27_unknown_beyond_horizon_blocks_automatic_resend(rt, db, clock):
    op = _standalone_charge(rt, db)
    fault(db, "payment", "create_checkout", "create_checkout", "timeout_before_effect")
    fault(db, "payment", "query", "query", "timeout_before_effect")
    rt.executor.submit(op.id, **ARGS)
    rt.executor.reconcile(op.id)
    db.expire_all()
    assert db.get(FinancialOperation, op.id).state == OpState.UNKNOWN
    clock.advance(hours=25)
    result = rt.executor.reconcile(op.id)
    assert result.state == OpState.RECONCILING
    assert _cases(db, "unknown_beyond_horizon", str(op.id))
    assert db.scalar(select(func.count()).where(SimPayment.client_key == op.idempotency_key)) == 0


def test_inside_horizon_not_found_is_replayed_with_the_same_key(rt, db):
    op = _standalone_charge(rt, db)
    fault(db, "payment", "create_checkout", "create_checkout", "timeout_before_effect")
    rt.executor.submit(op.id, **ARGS)
    result = rt.executor.reconcile(op.id)
    assert result.state == OpState.PENDING and result.external_ref
    assert db.scalar(select(func.count()).where(SimPayment.client_key == op.idempotency_key)) == 1


def test_t51_crash_after_provider_accepted_before_local_write(rt, db):
    """The provider acted but the process died before recording the result. Recovery looks the
    operation up instead of sending a new one."""
    op = _standalone_charge(rt, db)
    with rt.sessions() as s, s.begin():
        row = s.get(FinancialOperation, op.id, with_for_update=True)
        row.state, row.submitted_at, row.version = OpState.SUBMITTED, rt.clock.now(), 2
        row.request_args = ARGS
    rt.payments.create_checkout(idempotency_key=op.idempotency_key, amount_minor=5000, **ARGS)
    # ...crash: nothing recorded locally. On restart the reconciler runs:
    result = rt.executor.reconcile(op.id)
    assert result.state == OpState.PENDING and result.external_ref
    assert db.scalar(select(func.count()).where(SimPayment.client_key == op.idempotency_key)) == 1


def test_operation_key_reuse_with_different_amount_conflicts(rt, db):
    op = _standalone_charge(rt, db)
    with pytest.raises(TrollieError, match="different content"):
        create_operation(
            db,
            order_id=None,
            action=Action.CHARGE,
            profile=PROFILES["simpay-instant"],
            amount_minor=9999,
            idempotency_key=op.idempotency_key,
            request={},
            subject_type="test",
        )
    db.rollback()


def test_beyond_provider_horizon_provider_would_double_charge_which_is_why_we_block(rt, db, clock):
    """Documents the hazard: after the horizon, the provider treats the same key as new."""
    key = f"hazard:{uuid.uuid4()}"
    rt.payments.create_checkout(idempotency_key=key, amount_minor=100, **ARGS)
    clock.advance(hours=25)
    rt.payments.create_checkout(idempotency_key=key, amount_minor=100, **ARGS)
    assert db.scalar(select(func.count()).where(SimPayment.client_key == key)) == 2


# --- State machines ------------------------------------------------------------------


@settings(deadline=None)
@given(st.sampled_from(MACHINES), st.lists(st.integers(0, 50), max_size=30))
def test_property_state_machines_only_follow_declared_transitions(machine, choices):
    class Obj:
        pass

    obj = Obj()
    obj.state = sorted(machine.transitions)[0]
    obj.version = 1
    for choice in choices:
        targets = sorted(machine.states)
        target = targets[choice % len(targets)]
        before = (obj.state, obj.version)
        try:
            machine.move(obj, target)
        except TrollieError:
            assert obj.state == before[0] and obj.version == before[1]
            assert not machine.can(before[0], target) and before[0] != target
            continue
        if before[0] == target:
            assert obj.version == before[1]
        else:
            assert machine.can(before[0], target) and obj.version == before[1] + 1

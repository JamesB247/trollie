"""Order execution on both simulated rails: happy paths and fulfilment."""

from sqlalchemy import func, select

from app.ledger import chart
from app.ledger.service import account, balance
from app.orders.models import DeliveryJob, Order, OrderLeg
from app.orders.service import courier_progress, merchant_ready
from app.orders.status import order_status
from app.payments.models import FinancialOperation, OpState
from app.simulators.models import SimPayment
from tests.order_support import ledger_net_zero, pay, payable, purchase

CARD = "pay_per_order:card_auth_capture"
INSTANT = "pay_per_order:immediate"


def _ops(db, order_id):
    return {
        op.action: op
        for op in db.scalars(
            select(FinancialOperation).where(FinancialOperation.order_id == order_id)
        )
    }


def _deliver_all(rt, db, order_id):
    for leg in db.scalars(select(OrderLeg).where(OrderLeg.order_id == order_id)):
        if leg.state != "ACCEPTED":
            continue
        merchant_ready(rt, leg_id=leg.id)
        job = db.scalars(select(DeliveryJob).where(DeliveryJob.order_leg_id == leg.id)).one()
        courier_progress(rt, job_id=job.id, to="collected")
        courier_progress(rt, job_id=job.id, to="delivered")
    db.expire_all()


def test_card_two_store_purchase_happy_path(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=CARD)
    total = p.quote.total_minor
    assert len(p.quote.snapshot["legs"]) == 2
    status = order_status(db, p.order_id, p.customer.account_id)
    assert status["state"] == "PAYMENT_PENDING" and status["money"]["charged_minor"] == 0

    sellers = [leg["seller"]["merchant_id"] for leg in p.quote.snapshot["legs"]]
    before = {m: payable(db, m) for m in sellers}
    db.rollback()
    pay(rt, p.checkout_ref)
    db.expire_all()
    order = db.get(Order, p.order_id)
    assert order.state == "FULFILLING", order.attention_reason
    ops = _ops(db, p.order_id)
    assert ops["authorise"].state == OpState.SUCCEEDED
    assert ops["capture"].state == OpState.SUCCEEDED and ops["capture"].amount_minor == total
    assert (
        db.scalar(
            select(func.count()).where(SimPayment.client_key == ops["capture"].idempotency_key)
        )
        == 1
    )
    legs = db.scalars(select(OrderLeg).where(OrderLeg.order_id == p.order_id)).all()
    assert {leg.state for leg in legs} == {"ACCEPTED"}
    assert all(
        db.scalars(select(DeliveryJob).where(DeliveryJob.order_leg_id == leg.id)).one().state
        == "BOOKED"
        for leg in legs
    )
    status = order_status(db, p.order_id, p.customer.account_id)["money"]
    assert status["charged_minor"] == total and status["bank_hold_minor"] == 0

    # Ledger: collected funds allocated to each seller, the courier and the platform.
    snap = p.quote.snapshot
    for leg in snap["legs"]:
        merchant = leg["seller"]["merchant_id"]
        assert payable(db, merchant) - before[merchant] == leg["goods_minor"]
    assert ledger_net_zero(db)

    _deliver_all(rt, db, p.order_id)
    assert db.get(Order, p.order_id).state == "COMPLETED"


def test_immediate_payment_happy_path(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=INSTANT)
    pay(rt, p.checkout_ref)
    db.expire_all()
    assert db.get(Order, p.order_id).state == "FULFILLING"
    ops = _ops(db, p.order_id)
    assert set(ops) == {"charge"} and ops["charge"].state == OpState.SUCCEEDED
    clearing = account(db, chart.PROVIDER_CLEARING, None)
    assert balance(db, clearing) >= p.quote.total_minor
    _deliver_all(rt, db, p.order_id)
    assert db.get(Order, p.order_id).state == "COMPLETED"


def test_customer_declines_payment(rt, db, split_world):
    p = purchase(rt, db, split_world, funding=CARD)
    pay(rt, p.checkout_ref, approve=False)
    db.expire_all()
    order = db.get(Order, p.order_id)
    assert order.state == "CANCELLED" and order.attention_reason == "payment_failed"
    assert {
        leg.state for leg in db.scalars(select(OrderLeg).where(OrderLeg.order_id == p.order_id))
    } == {"RESERVED"}

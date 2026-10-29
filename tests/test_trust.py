"""Trust controls found necessary by the round-2 crowd simulation (I-043..I-047): a merchant
that takes paid orders and never hands them over, stolen money loaded into a wallet, a
hijacked agent, and a store whose integration keeps timing out."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.errors import ErrorCode, TrollieError
from app.merchants.adapter import MerchantTimeout
from app.merchants.health import HealthCheckedMerchant
from app.merchants.models import Merchant, MerchantState
from app.merchants.risk import over_exposure_cap, review_deliveries
from app.orders.handlers import pump
from app.orders.models import Order, OrderLeg
from app.orders.status import order_status
from app.wallet import service as wallet_svc
from app.wallet.models import Grant, Wallet
from tests.flows import estimate, firm, new_customer, shopping_list
from tests.order_support import ZONE, pay, purchase
from tests.test_api import User
from tests.test_api import api as api  # noqa: F401 - fixture
from tests.test_wallet import funded, topup, tx

CARD = "pay_per_order:card_auth_capture"


@pytest.fixture
def probation_b(db, split_world):
    """Store B is a newly onboarded merchant for the duration of a test."""
    mid = split_world["merchant:b"]
    with tx(db):
        db.get(Merchant, mid).risk_tier = "probation"
    yield mid
    with tx(db):
        m = db.get(Merchant, mid)
        m.risk_tier, m.state = "standard", MerchantState.PAYMENT_ENABLED


def _legs(db, order_id):
    db.expire_all()
    return {
        leg.leg_id: leg for leg in db.scalars(select(OrderLeg).where(OrderLeg.order_id == order_id))
    }


def _past_windows(clock, db, order_ids):
    latest = max(leg.window_end for oid in order_ids for leg in _legs(db, oid).values())
    clock.advance(seconds=(latest - clock.now()).total_seconds())
    clock.advance(minutes=get_settings().delivery_grace_minutes + 1)


def test_merchant_that_never_hands_over_is_suspended_and_customers_refunded(
    rt, db, split_world, clock, probation_b
):
    orders = []
    for _ in range(3):
        p = purchase(rt, db, split_world, funding=CARD)
        pay(rt, p.checkout_ref)
        orders.append(p)
    _past_windows(clock, db, [p.order_id for p in orders])
    review_deliveries(rt)
    pump(rt, rt.payments)
    db.expire_all()
    assert db.get(Merchant, probation_b).state == MerchantState.SUSPENDED
    for p in orders:
        legs = _legs(db, p.order_id).values()
        b_leg = next(leg for leg in legs if leg.merchant_id == probation_b)
        money = order_status(db, p.order_id, p.customer.account_id)["money"]
        back = money["refund_requested_minor"] + money["refund_confirmed_minor"]
        assert back == b_leg.goods_minor + b_leg.delivery_minor  # without asking
        assert db.get(Order, p.order_id).attention_reason == "delivery_overdue"
    # The standard merchant A was equally late here, but is only flagged, not suspended.
    assert db.get(Merchant, split_world["merchant:a"]).state == MerchantState.PAYMENT_ENABLED


def test_suspended_merchant_gets_no_reservation(rt, db, split_world, probation_b):
    customer = new_customer(db, zone=ZONE)
    sid = shopping_list(db, split_world, customer, [("a-rice", {}), ("b-tea", {})])
    est = estimate(db, customer, sid, rt.clock)
    with tx(db):
        db.get(Merchant, probation_b).state = MerchantState.SUSPENDED
    with pytest.raises(TrollieError) as err:
        firm(rt.sessions, rt.merchant, customer, est.id, rt.clock, funding=CARD)
    assert err.value.code is ErrorCode.REAPPROVAL_REQUIRED


def test_probation_merchant_over_exposure_cap_leaves_new_baskets(
    rt, db, split_world, probation_b, monkeypatch
):
    p = purchase(rt, db, split_world, funding=CARD)
    pay(rt, p.checkout_ref)
    monkeypatch.setattr(get_settings(), "probation_exposure_cap_minor", 1)
    assert probation_b in over_exposure_cap(db)
    customer = new_customer(db, zone=ZONE)
    sid = shopping_list(db, split_world, customer, [("b-tea", {})])
    with pytest.raises(AssertionError, match="unavailable"):
        estimate(db, customer, sid, rt.clock)


def test_not_delivered_claim_only_after_window_and_only_if_never_handed_over(
    rt, db, split_world, clock
):
    from app.api.routes import _check_not_delivered
    from app.orders.service import courier_progress, merchant_ready

    p = purchase(rt, db, split_world, funding=CARD)
    pay(rt, p.checkout_ref)
    order = db.get(Order, p.order_id)
    legs = _legs(db, p.order_id)
    with pytest.raises(TrollieError, match="has not passed"):
        _check_not_delivered(db, order, "leg_1", clock.now())
    # Leg 2 is handed to the courier: late, but on its way, so no refund for goods coming.
    leg2 = legs["leg_2"]
    merchant_ready(rt, leg_id=leg2.id)
    from app.orders.models import DeliveryJob

    job = db.scalars(select(DeliveryJob).where(DeliveryJob.order_leg_id == leg2.id)).one()
    courier_progress(rt, job_id=job.id, to="collected")
    _past_windows(clock, db, [p.order_id])
    db.expire_all()
    _check_not_delivered(db, order, "leg_1", clock.now())  # never handed over: accepted
    with pytest.raises(TrollieError, match="on its way"):
        _check_not_delivered(db, order, "leg_2", clock.now())


def _now_is_real(rt):
    """Ledger rows are stamped by the database; line the test clock up with it."""
    rt.clock.advance(seconds=(datetime.now(UTC) - rt.clock.now()).total_seconds())


def test_new_topup_spendable_only_up_to_allowance_and_not_withdrawable(rt, db, split_world):
    _now_is_real(rt)
    allowance = get_settings().wallet_clearing_allowance_minor
    customer, wallet = funded(rt, db, amount=allowance + 500_000)
    with tx(db):
        available, held = wallet_svc.spendable_now(db, wallet.id, rt.clock.now())
    assert available == allowance and held == 500_000
    with pytest.raises(TrollieError) as err, tx(db):
        wallet_svc.request_redemption(
            db, owner_account_id=customer.account_id, amount_minor=1,
            business_key=str(uuid.uuid4()), now=rt.clock.now(),
        )  # fmt: skip
    assert err.value.code is ErrorCode.FUNDS_ON_HOLD
    rt.clock.advance(minutes=get_settings().wallet_clearing_minutes + 1)
    with tx(db):
        available, held = wallet_svc.spendable_now(db, wallet.id, rt.clock.now())
    assert held == 0 and available == allowance + 500_000


def test_recalled_topup_restricts_the_wallet_but_system_steps_still_run(rt, db):
    customer, wallet = funded(rt, db, amount=20_000)
    intent = topup(rt, db, wallet, 30_000)
    rt.payments.incoming_transfer(
        transfer_ref=intent.transfer_ref, reference=wallet.funding_reference,
        amount_minor=30_000, status="reversed",
    )  # fmt: skip
    pump(rt, rt.payments)
    db.expire_all()
    assert db.get(Wallet, wallet.id).status == "restricted"
    with pytest.raises(TrollieError) as err, tx(db):
        wallet_svc.request_redemption(
            db, owner_account_id=customer.account_id, amount_minor=1,
            business_key=str(uuid.uuid4()), now=rt.clock.now(),
        )  # fmt: skip
    assert err.value.code is ErrorCode.FUNDS_ON_HOLD
    # A second recall into the restricted wallet is still processed, not stuck in a retry loop.
    second = topup(rt, db, wallet, 5_000)
    rt.payments.incoming_transfer(
        transfer_ref=second.transfer_ref, reference=wallet.funding_reference,
        amount_minor=5_000, status="reversed",
    )  # fmt: skip
    pump(rt, rt.payments)
    db.expire_all()
    from app.wallet.models import FundingIntent

    assert db.get(FundingIntent, second.id).state == "reversed"


def _agent(user: User, api):
    user.call("POST", "/v1/wallet")
    a = user.call("POST", "/v1/agents", json={"name": "helper"}).json()
    grant = user.call(
        "POST",
        f"/v1/agents/{a['agent_id']}/grants",
        json={"approval_mode": "per_quote", "address_version_id": user.address,
              "per_order_cap_minor": 50_000, "period_cap_minor": 100_000},
    ).json()  # fmt: skip
    return a, grant, {"Authorization": f"Bearer {a['agent_token']}"}


def test_agent_that_keeps_overstepping_is_suspended(api, db):  # noqa: F811
    user = User(api)
    a, grant, h = _agent(user, api)
    for _ in range(get_settings().agent_strike_limit):
        r = api.post(
            f"/v1/agents/{a['agent_id']}/grants",
            headers=h,
            json={"approval_mode": "mandate", "address_version_id": user.address,
                  "per_order_cap_minor": 9_000_000, "period_cap_minor": 9_000_000},
        )  # fmt: skip
        assert r.status_code == 403
    r = api.get("/v1/catalogue/products", headers=h)  # even a harmless call is now refused
    assert r.status_code == 403 and "suspended" in r.json()["message"]
    db.expire_all()
    assert db.get(Grant, uuid.UUID(grant["grant_id"])).status == "suspended"
    assert api.get("/v1/catalogue/products", headers=user.headers).status_code == 200


def test_agent_purchase_requests_are_rate_limited(api, catalogue):  # noqa: F811
    from tests.test_api import basket

    user = User(api)
    a, _, h = _agent(user, api)
    sid = basket(user, catalogue, items=(("tea-100", 1),))
    est = api.post(f"/v1/shopping-sessions/{sid}/quotes", headers=h, json={}).json()
    qid = est["options"]["cheapest"]["quote_id"]
    codes = [
        api.post("/v1/purchase-requests", headers=h, json={"quote_id": qid}).status_code
        for _ in range(get_settings().agent_requests_per_window + 1)
    ]
    assert codes[:-1] == [202] * get_settings().agent_requests_per_window
    assert codes[-1] == 429


class _Flaky:
    def __init__(self):
        self.calls = 0

    def prepare_reservation(self, *, location_id, client_ref, lines):
        self.calls += 1
        raise MerchantTimeout(client_ref)


def test_store_that_keeps_timing_out_is_left_out_for_a_while():
    inner = _Flaky()
    m = HealthCheckedMerchant(inner)
    loc = uuid.uuid4()
    for i in range(get_settings().merchant_circuit_failures):
        assert loc not in m.unavailable()
        with pytest.raises(MerchantTimeout):
            m.prepare_reservation(location_id=loc, client_ref=f"r{i}", lines=[])
    assert loc in m.unavailable()


@pytest.mark.parametrize(
    ("tier", "stuck", "claims", "delivered", "suspend"),
    [
        ("probation", 2, 0, 0, True),  # never delivered anything, two legs overdue
        ("probation", 2, 0, 5, False),  # has a delivery record: one more chance
        ("probation", 3, 0, 5, True),
        ("probation", 0, 2, 5, True),  # two non-delivery claims
        ("standard", 9, 9, 0, False),  # an established merchant is flagged, not suspended
    ],
)
def test_suspension_rule(tier, stuck, claims, delivered, suspend):
    from app.merchants.risk import should_suspend

    assert should_suspend(tier, stuck=stuck, claims=claims, delivered=delivered) is suspend


def test_non_delivery_claim_refunds_what_is_left_of_the_leg(rt, db, split_world, clock):
    from app.orders.service import create_refund, remaining_leg_value

    p = purchase(rt, db, split_world, funding=CARD)
    pay(rt, p.checkout_ref)
    order = db.get(Order, p.order_id)
    leg = _legs(db, p.order_id)["leg_1"]
    line = p.quote.snapshot["legs"][0]["lines"][0]
    create_refund(
        rt, order_id=order.id, business_key=f"t:{uuid.uuid4()}", reason="missing_item",
        parties=[{"party_type": "merchant", "party_id": str(leg.merchant_id),
                  "amount_minor": line["line_total_minor"], "leg_id": "leg_1",
                  "line_id": line["line_id"]}],
    )  # fmt: skip
    db.expire_all()
    with tx(db):
        left = remaining_leg_value(db, db.get(Order, order.id), _legs(db, order.id)["leg_1"])
    assert left == leg.goods_minor + leg.delivery_minor - line["line_total_minor"]


def test_courier_failure_lets_the_customer_claim_at_once(rt, db, split_world, clock):
    from app.api.routes import _check_not_delivered
    from app.orders.models import DeliveryJob
    from app.orders.service import courier_progress, merchant_ready

    p = purchase(rt, db, split_world, funding=CARD)
    pay(rt, p.checkout_ref)
    leg = _legs(db, p.order_id)["leg_1"]
    merchant_ready(rt, leg_id=leg.id)
    job = db.scalars(select(DeliveryJob).where(DeliveryJob.order_leg_id == leg.id)).one()
    courier_progress(rt, job_id=job.id, to="collected")
    courier_progress(rt, job_id=job.id, to="failed")
    db.expire_all()
    _check_not_delivered(db, db.get(Order, p.order_id), "leg_1", clock.now())  # no wait

"""Synthetic wallet acceptance tests W01-W19 (addendum §8; W05 as amended by A3).
W20 (synthetic database under a live runtime) is in test_startup_guards.py."""

import threading
import uuid
from contextlib import contextmanager
from datetime import timedelta

import pytest
from sqlalchemy import func, select, text

from app.errors import ErrorCode, TrollieError
from app.ledger import chart
from app.ledger.service import account, balance
from app.orders.handlers import pump
from app.orders.models import Order, OrderLeg
from app.orders.service import create_order, request_cancellation
from app.payments.models import FinancialOperation
from app.quotes.models import Quote
from app.reconciliation.models import ReconciliationCase
from app.simulators.models import SimPayment
from app.wallet import service as wallet_svc
from app.wallet.grants import create_grant, deny_agent_action, revoke_grant
from app.wallet.models import Agent, GrantUsage, WalletReservation
from app.wallet.orders import execute_under_mandate, refund_wallet_order
from tests.flows import approve, estimate, firm, new_customer, register_passkey, shopping_list
from tests.order_support import ZONE
from tests.test_compensation import fault

ITEMS = [("a-rice", {}), ("b-tea", {})]  # two legs, small basket


@contextmanager
def tx(db):
    """Begin a transaction on the shared test session, committing any implicit one first."""
    if db.in_transaction():
        db.commit()
    with db.begin():
        yield


def topup(rt, db, wallet, amount, *, status="confirmed", deliveries=1, reference=None):
    with tx(db):
        intent = wallet_svc.create_funding_intent(db, wallet_id=wallet.id, amount_minor=amount)
    rt.payments.incoming_transfer(
        transfer_ref=intent.transfer_ref,
        reference=reference or wallet.funding_reference,
        amount_minor=amount,
        status=status,
        deliveries=deliveries,
    )
    pump(rt, rt.payments)
    return intent


def funded(rt, db, amount=200_000):
    customer = new_customer(db, zone=ZONE)
    with tx(db):
        wallet = wallet_svc.open_wallet(db, account_id=customer.account_id)
    topup(rt, db, wallet, amount)
    return customer, wallet


def bal(db, wallet):
    db.expire_all()
    with tx(db):
        return wallet_svc.balances(db, wallet.id)


def agent_envelope(rt, db, customer, *, allocate=150_000, mode="per_quote", **grant_kw):
    with tx(db):
        agent = Agent(account_id=customer.account_id, name="grocery agent (fixture)")
        db.add(agent)
        db.flush()
        envelope = wallet_svc.create_envelope(
            db, owner_account_id=customer.account_id, agent_id=agent.id, label="groceries"
        )
        if allocate:
            wallet_svc.allocate(
                db,
                owner_account_id=customer.account_id,
                envelope_id=envelope.id,
                amount_minor=allocate,
                business_key=str(uuid.uuid4()),
            )
        kw = {
            "per_order_cap_minor": 50_000,
            "period_cap_minor": 100_000,
            "valid_from": rt.clock.now() - timedelta(minutes=1),
            "valid_until": rt.clock.now() + timedelta(days=30),
        } | grant_kw
        grant = create_grant(
            db,
            owner_account_id=customer.account_id,
            agent_id=agent.id,
            approval_mode=mode,
            address_version_id=customer.address_id,
            **kw,
        )
    return agent, envelope, grant


def wallet_quote(rt, db, world, customer, funding, items=ITEMS):
    session_id = shopping_list(db, world, customer, items)
    est = estimate(db, customer, session_id, rt.clock)
    result = firm(rt.sessions, rt.merchant, customer, est.id, rt.clock, funding=funding)
    assert result.quote is not None, result.blocking
    return result.quote


def owner_buys(rt, db, world, customer, funding):
    quote = wallet_quote(rt, db, world, customer, funding)
    if customer.authenticator is None:
        register_passkey(db, customer, rt.clock)
    approval = approve(db, customer, quote.id, rt.clock)
    order_id = create_order(rt, account_id=customer.account_id, approval_id=approval.id)
    pump(rt, rt.payments)
    return quote, order_id


def mandate(rt, db, customer, **kw):
    rt.mandate_fixture_enabled = True
    agent, envelope, grant = agent_envelope(rt, db, customer, mode="mandate", **kw)
    if customer.authenticator is None:
        register_passkey(db, customer, rt.clock)
    approve(db, customer, grant.id, rt.clock, subject_type="mandate")
    return agent, envelope, grant


def state(db, order_id):
    db.expire_all()
    return db.get(Order, order_id).state


# --- W1: funding and ownership -------------------------------------------------------


def test_w01_duplicate_confirmed_topup_credits_once(rt, db):
    customer, wallet = funded(rt, db, amount=10_000)
    intent = topup(rt, db, wallet, 5_000, deliveries=3)  # the provider sends it three times
    rt.payments.incoming_transfer(
        transfer_ref=intent.transfer_ref,  # and once more, new id
        reference=wallet.funding_reference,
        amount_minor=5_000,
    )
    pump(rt, rt.payments)
    assert bal(db, wallet)["unallocated_minor"] == 15_000


@pytest.mark.parametrize("status", ["pending", "failed"])
def test_w02_pending_or_failed_topup_is_not_spendable(rt, db, status):
    customer, wallet = funded(rt, db, amount=1_000)
    topup(rt, db, wallet, 50_000, status=status)
    b = bal(db, wallet)
    assert b["unallocated_minor"] == 1_000
    assert b["pending_topups_minor"] == (50_000 if status == "pending" else 0)


@pytest.mark.parametrize("variant", ["currency", "destination", "reference", "amount"])
def test_w03_mismatched_topup_goes_to_suspense_or_quarantine(rt, db, variant):
    customer = new_customer(db, zone=ZONE)
    with tx(db):
        wallet = wallet_svc.open_wallet(db, account_id=customer.account_id)
        intent = wallet_svc.create_funding_intent(db, wallet_id=wallet.id, amount_minor=7_000)
    kw = {
        "transfer_ref": intent.transfer_ref,
        "reference": wallet.funding_reference,
        "amount_minor": 7_000,
    }
    if variant == "currency":
        kw["currency"] = "USD"
    elif variant == "destination":
        kw["destination_account"] = "someone-else"
    elif variant == "reference":
        kw["reference"] = "TRL-UNKNOWN"
    else:
        kw["amount_minor"] = 7_001
    rt.payments.incoming_transfer(**kw)
    pump(rt, rt.payments)
    assert bal(db, wallet)["unallocated_minor"] == 0  # never guessed into a wallet
    expected = (
        "funding_quarantined" if variant in ("currency", "destination") else "unmatched_funds"
    )
    assert db.scalars(
        select(ReconciliationCase).where(
            ReconciliationCase.case_type == expected,
            ReconciliationCase.refs["transfer_ref"].astext == intent.transfer_ref,
        )
    ).first()


def test_w04_concurrent_allocation_never_exceeds_owner_funds(rt, db, sessions):
    customer, wallet = funded(rt, db, amount=10_000)
    with tx(db):
        envelopes = [
            wallet_svc.create_envelope(
                db, owner_account_id=customer.account_id, agent_id=None, label=f"e{i}"
            )
            for i in range(4)
        ]
    results = []
    barrier = threading.Barrier(4)

    def go(env):
        barrier.wait()
        with sessions() as s:
            try:
                with s.begin():
                    wallet_svc.allocate(
                        s,
                        owner_account_id=customer.account_id,
                        envelope_id=env.id,
                        amount_minor=4_000,
                        business_key=str(uuid.uuid4()),
                    )
                results.append("ok")
            except TrollieError:
                results.append("refused")

    threads = [threading.Thread(target=go, args=(e,)) for e in envelopes]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count("ok") == 2
    b = bal(db, wallet)
    assert b["unallocated_minor"] == 2_000 and b["total_minor"] == 10_000


# --- W2/W3: purchases, grants and races --------------------------------------------


def test_w16_wallet_purchase_has_no_external_debit(rt, db, split_world):
    customer, wallet = funded(rt, db, amount=100_000)

    def payables():
        with tx(db):
            return {
                m: balance(db, account(db, chart.MERCHANT_PAYABLE, split_world[f"merchant:{m}"]))
                for m in ("a", "b")
            }

    before = payables()
    quote, order_id = owner_buys(rt, db, split_world, customer, "wallet:unallocated")
    assert state(db, order_id) == "FULFILLING"
    assert (
        db.scalar(
            select(func.count())
            .select_from(FinancialOperation)
            .where(FinancialOperation.order_id == order_id)
        )
        == 0
    )
    assert db.scalar(select(func.count()).where(SimPayment.reference == f"order-{order_id}")) == 0
    b = bal(db, wallet)
    assert b["unallocated_minor"] == 100_000 - quote.total_minor and b["reserved_minor"] == 0
    after = payables()
    owed = {split_world["merchant:a"]: "a", split_world["merchant:b"]: "b"}
    for leg in quote.snapshot["legs"]:  # this purchase made each seller owed its goods
        m = owed[uuid.UUID(leg["seller"]["merchant_id"])]
        assert after[m] - before[m] >= leg["goods_minor"]


def test_w06_funds_without_authority_is_refused(rt, db, split_world):
    customer, wallet = funded(rt, db)
    agent, envelope, grant = agent_envelope(rt, db, customer, mode="per_quote")
    quote = wallet_quote(rt, db, split_world, customer, f"wallet:envelope:{envelope.id}")
    rt.mandate_fixture_enabled = True
    with pytest.raises(TrollieError) as err:  # per-quote grant: the agent cannot execute
        execute_under_mandate(rt, agent_id=agent.id, quote_id=quote.id)
    assert err.value.code is ErrorCode.AUTHORITY_DENIED
    with pytest.raises(TrollieError):  # and there is no approval to create an order from
        create_order(rt, account_id=customer.account_id, approval_id=uuid.uuid4())


def test_w07_authority_without_funds_is_refused(rt, db, split_world):
    customer, wallet = funded(rt, db, amount=500)
    with pytest.raises(TrollieError) as err:
        wallet_quote(rt, db, split_world, customer, "wallet:unallocated")
    assert err.value.code is ErrorCode.INSUFFICIENT_FUNDS


def test_w07_funds_spent_after_quote_refused_at_reservation(rt, db, split_world):
    customer, wallet = funded(rt, db, amount=30_000)
    quote = wallet_quote(rt, db, split_world, customer, "wallet:unallocated")
    register_passkey(db, customer, rt.clock)
    approval = approve(db, customer, quote.id, rt.clock)
    with tx(db):  # the owner withdraws most of the money before execution
        wallet_svc.request_redemption(
            db,
            owner_account_id=customer.account_id,
            amount_minor=29_000,
            business_key=str(uuid.uuid4()),
            now=rt.clock.now(),
        )
    with pytest.raises(TrollieError) as err:
        create_order(rt, account_id=customer.account_id, approval_id=approval.id)
    assert err.value.code is ErrorCode.INSUFFICIENT_FUNDS
    assert bal(db, wallet)["unallocated_minor"] == 1_000  # no overdraft, nothing reserved


def test_w08_agent_cannot_widen_its_own_authority(rt, db):
    customer, wallet = funded(rt, db)
    agent, envelope, grant = agent_envelope(rt, db, customer)
    for action in ("allocate_funds", "broaden_grant", "change_address", "change_payee"):
        with pytest.raises(TrollieError) as err:
            deny_agent_action(db, agent_id=agent.id, action=action)
        assert err.value.code is ErrorCode.AUTHORITY_DENIED
    db.rollback()
    other = new_customer(db, zone=ZONE)
    with pytest.raises(TrollieError), tx(db):  # nor can anyone but the owner grant
        create_grant(
            db,
            owner_account_id=other.account_id,
            agent_id=agent.id,
            approval_mode="mandate",
            address_version_id=other.address_id,
            per_order_cap_minor=1,
            period_cap_minor=1,
            valid_from=rt.clock.now(),
            valid_until=rt.clock.now() + timedelta(days=1),
        )


def test_mandate_requires_passkey_approval_and_fixture_flag(rt, db, split_world):
    customer, wallet = funded(rt, db)
    rt.mandate_fixture_enabled = True
    agent, envelope, grant = agent_envelope(rt, db, customer, mode="mandate")
    quote = wallet_quote(rt, db, split_world, customer, f"wallet:envelope:{envelope.id}")
    with pytest.raises(TrollieError) as err:  # not yet approved by the owner
        execute_under_mandate(rt, agent_id=agent.id, quote_id=quote.id)
    assert err.value.details.get("reason") == "no_grant"
    register_passkey(db, customer, rt.clock)
    approve(db, customer, grant.id, rt.clock, subject_type="mandate")
    rt.mandate_fixture_enabled = False
    with pytest.raises(TrollieError) as err:
        execute_under_mandate(rt, agent_id=agent.id, quote_id=quote.id)
    assert err.value.code is ErrorCode.CAPABILITY_NOT_ENABLED
    rt.mandate_fixture_enabled = True
    order_id = execute_under_mandate(rt, agent_id=agent.id, quote_id=quote.id)
    assert state(db, order_id) == "FULFILLING"
    assert db.get(Order, order_id).approval_id is None  # authority is the mandate execution


def test_w09_revocation_between_request_and_commitment_stops(rt, db, split_world):
    customer, wallet = funded(rt, db)
    agent, envelope, grant = mandate(rt, db, customer)
    quote = wallet_quote(rt, db, split_world, customer, f"wallet:envelope:{envelope.id}")
    # Merchant commitment is slow: the first commit attempt times out with no lookup answer.
    fault(
        db,
        "merchant",
        quote.snapshot["legs"][0]["location_id"],
        "commit_order",
        "timeout_before_effect",
    )
    fault(
        db,
        "merchant",
        quote.snapshot["legs"][0]["location_id"],
        "get_order",
        "timeout_before_effect",
    )
    order_id = execute_under_mandate(rt, agent_id=agent.id, quote_id=quote.id)
    with tx(db):
        revoke_grant(
            db, owner_account_id=customer.account_id, grant_id=grant.id, now=rt.clock.now()
        )
    pump(rt, rt.payments)
    assert state(db, order_id) == "CANCELLED"
    assert db.get(Order, order_id).attention_reason == "grant_revoked"
    b = bal(db, wallet)
    assert b["reserved_minor"] == 0 and b["envelopes_minor"][str(envelope.id)] == 150_000


def test_w10_no_release_while_merchant_state_is_uncertain(rt, db, split_world):
    customer, wallet = funded(rt, db)
    quote = wallet_quote(rt, db, split_world, customer, "wallet:unallocated")
    loc = quote.snapshot["legs"][1]["location_id"]
    fault(db, "merchant", loc, "commit_order", "timeout_after_effect", times=1)
    fault(db, "merchant", loc, "get_order", "timeout_before_effect", times=100)
    register_passkey(db, customer, rt.clock)
    approval = approve(db, customer, quote.id, rt.clock)
    order_id = create_order(rt, account_id=customer.account_id, approval_id=approval.id)
    pump(rt, rt.payments)
    request_cancellation(rt, account_id=customer.account_id, order_id=order_id)
    pump(rt, rt.payments)
    assert bal(db, wallet)["reserved_minor"] == quote.total_minor  # still held: not yet safe
    with tx(db):
        db.execute(text("DELETE FROM sim_faults"))
    pump(rt, rt.payments)  # the merchant answers; the cancellation completes
    assert state(db, order_id) == "CANCELLED"
    assert bal(db, wallet)["reserved_minor"] == 0
    legs = db.scalars(select(OrderLeg).where(OrderLeg.order_id == order_id)).all()
    assert {leg.state for leg in legs} == {"CANCELLED"}


def test_w11_release_delivered_twice_restores_once(rt, db, split_world):
    customer, wallet = funded(rt, db, amount=100_000)
    quote = wallet_quote(rt, db, split_world, customer, "wallet:unallocated")
    register_passkey(db, customer, rt.clock)
    approval = approve(db, customer, quote.id, rt.clock)
    order_id = create_order(rt, account_id=customer.account_id, approval_id=approval.id)
    with tx(db):
        assert wallet_svc.release(db, order_id=order_id) is True
    with tx(db):
        assert wallet_svc.release(db, order_id=order_id) is False
    assert bal(db, wallet)["unallocated_minor"] == 100_000


def test_w05a_two_concurrent_reservations_cannot_overspend_one_envelope(rt, db, sessions):
    customer, wallet = funded(rt, db, amount=100_000)
    agent, envelope, grant = agent_envelope(rt, db, customer, allocate=60_000)
    results = []
    barrier = threading.Barrier(2)

    def go():
        barrier.wait()
        with sessions() as s:
            try:
                with s.begin():
                    wallet_svc.reserve(
                        s,
                        account_id=customer.account_id,
                        order_id=uuid.uuid4(),
                        funding_source=f"wallet:envelope:{envelope.id}",
                        amount_minor=40_000,
                    )
                results.append("ok")
            except TrollieError:
                results.append("refused")

    threads = [threading.Thread(target=go) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == ["ok", "refused"]
    b = bal(db, wallet)
    assert b["envelopes_minor"][str(envelope.id)] == 20_000 and b["reserved_minor"] == 40_000


@pytest.mark.parametrize("owner_action", ["deallocate", "redeem"])
def test_w05b_w14_reserve_racing_owner_withdrawal(rt, db, sessions, owner_action):
    customer, wallet = funded(rt, db, amount=50_000)
    agent, envelope, grant = agent_envelope(rt, db, customer, allocate=50_000)
    results = {}
    barrier = threading.Barrier(2)

    def agent_reserve():
        barrier.wait()
        with sessions() as s:
            try:
                with s.begin():
                    wallet_svc.reserve(
                        s,
                        account_id=customer.account_id,
                        order_id=uuid.uuid4(),
                        funding_source=f"wallet:envelope:{envelope.id}",
                        amount_minor=40_000,
                    )
                results["agent"] = "ok"
            except TrollieError:
                results["agent"] = "refused"

    def owner():
        barrier.wait()
        with sessions() as s:
            try:
                with s.begin():
                    wallet_svc.deallocate(
                        s,
                        owner_account_id=customer.account_id,
                        envelope_id=envelope.id,
                        amount_minor=30_000,
                        business_key=str(uuid.uuid4()),
                    )
                    if owner_action == "redeem":
                        wallet_svc.request_redemption(
                            s,
                            owner_account_id=customer.account_id,
                            amount_minor=30_000,
                            business_key=str(uuid.uuid4()),
                            now=rt.clock.now(),
                        )
                results["owner"] = "ok"
            except TrollieError:
                results["owner"] = "refused"

    threads = [threading.Thread(target=f) for f in (agent_reserve, owner)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert list(results.values()).count("ok") == 1  # the same money cannot do both
    b = bal(db, wallet)
    assert all(v >= 0 for v in b["envelopes_minor"].values()) and b["unallocated_minor"] >= 0


def test_w05c_separate_envelopes_are_isolated(rt, db, split_world):
    customer, wallet = funded(rt, db, amount=100_000)
    agent_a, env_a, _ = agent_envelope(rt, db, customer, allocate=60_000)
    agent_b, env_b, _ = agent_envelope(rt, db, customer, allocate=10_000)
    with pytest.raises(TrollieError) as err, tx(db):
        wallet_svc.reserve(
            db,
            account_id=customer.account_id,
            order_id=uuid.uuid4(),
            funding_source=f"wallet:envelope:{env_b.id}",
            amount_minor=20_000,
        )
    assert err.value.code is ErrorCode.INSUFFICIENT_FUNDS  # never draws from envelope A
    assert bal(db, wallet)["envelopes_minor"][str(env_a.id)] == 60_000


def test_w12_partial_refunds_never_exceed_entitlement(rt, db, split_world):
    customer, wallet = funded(rt, db, amount=100_000)
    agent, envelope, grant = agent_envelope(rt, db, customer, allocate=80_000)
    quote, order_id = owner_buys(rt, db, split_world, customer, f"wallet:envelope:{envelope.id}")
    leg = quote.snapshot["legs"][0]
    part = [
        {
            "party_type": "merchant",
            "party_id": leg["seller"]["merchant_id"],
            "amount_minor": leg["goods_minor"],
        }
    ]
    first = refund_wallet_order(rt, order_id=order_id, business_key="r1", parties=part)
    assert refund_wallet_order(rt, order_id=order_id, business_key="r1", parties=part) == first
    big = [
        {
            "party_type": "merchant",
            "party_id": leg["seller"]["merchant_id"],
            "amount_minor": quote.total_minor,
        }
    ]
    with pytest.raises(TrollieError, match="exceeds"):
        refund_wallet_order(rt, order_id=order_id, business_key="r2", parties=big)
    # A5: the refund returned to the envelope it came from (grant still active).
    after = bal(db, wallet)
    assert (
        after["envelopes_minor"][str(envelope.id)]
        == 80_000 - quote.total_minor + leg["goods_minor"]
    )


def test_w13_confirmed_topup_later_reversed(rt, db, split_world):
    customer, wallet = funded(rt, db, amount=20_000)
    intent = topup(rt, db, wallet, 30_000)
    with tx(db):  # 40 000 of the 50 000 is moved into an envelope before the reversal
        envelope = wallet_svc.create_envelope(
            db, owner_account_id=customer.account_id, agent_id=None, label="x"
        )
        wallet_svc.allocate(
            db,
            owner_account_id=customer.account_id,
            envelope_id=envelope.id,
            amount_minor=40_000,
            business_key=str(uuid.uuid4()),
        )
    rt.payments.incoming_transfer(
        transfer_ref=intent.transfer_ref,
        reference=wallet.funding_reference,
        amount_minor=30_000,
        status="reversed",
    )
    pump(rt, rt.payments)
    b = bal(db, wallet)
    assert b["unallocated_minor"] == 0  # the free 10 000 was frozen and returned
    recovery = balance(db, account(db, chart.FUNDING_RECOVERY, wallet.id))
    assert recovery == 20_000  # the rest is a recorded recovery, not another customer's money
    assert db.scalars(
        select(ReconciliationCase).where(
            ReconciliationCase.case_type == "funding_recovery",
            ReconciliationCase.refs["transfer_ref"].astext == intent.transfer_ref,
        )
    ).one()


def test_w15_small_orders_cannot_evade_aggregate_caps(rt, db, split_world):
    customer, wallet = funded(rt, db, amount=200_000)
    agent, envelope, grant = mandate(
        rt, db, customer, per_order_cap_minor=20_000, period_cap_minor=15_000, max_orders_per_day=5
    )
    first = wallet_quote(
        rt, db, split_world, customer, f"wallet:envelope:{envelope.id}", items=[("a-rice", {})]
    )
    execute_under_mandate(rt, agent_id=agent.id, quote_id=first.id)
    second = wallet_quote(
        rt, db, split_world, customer, f"wallet:envelope:{envelope.id}", items=[("a-rice", {})]
    )
    with pytest.raises(TrollieError) as err:
        execute_under_mandate(rt, agent_id=agent.id, quote_id=second.id)
    assert err.value.details["reason"] == "period_cap"


def test_w17_customer_funds_and_operating_reserve_are_separate(rt, db, split_world):
    a, wallet_a = funded(rt, db, amount=5_000)
    b, wallet_b = funded(rt, db, amount=500_000)
    with pytest.raises(TrollieError) as err:
        wallet_quote(rt, db, split_world, a, "wallet:unallocated")
    assert err.value.code is ErrorCode.INSUFFICIENT_FUNDS  # B's money is never a subsidy
    db.expire_all()
    assert account(db, chart.OPERATING_RESERVE, None) not in {
        wallet_svc.unallocated_acct(db, wallet_a.id),
        wallet_svc.unallocated_acct(db, wallet_b.id),
    }
    assert bal(db, wallet_b)["unallocated_minor"] == 500_000


def test_w18_refund_restores_money_not_authority(rt, db, split_world):
    customer, wallet = funded(rt, db, amount=200_000)
    agent, envelope, grant = mandate(
        rt, db, customer, per_order_cap_minor=20_000, period_cap_minor=15_000
    )
    quote = wallet_quote(
        rt, db, split_world, customer, f"wallet:envelope:{envelope.id}", items=[("a-rice", {})]
    )
    order_id = execute_under_mandate(rt, agent_id=agent.id, quote_id=quote.id)
    used_before = db.scalar(
        select(func.sum(GrantUsage.amount_minor)).where(GrantUsage.grant_id == grant.id)
    )
    leg = quote.snapshot["legs"][0]
    refund_wallet_order(
        rt,
        order_id=order_id,
        business_key="w18",
        parties=[
            {
                "party_type": "merchant",
                "party_id": leg["seller"]["merchant_id"],
                "amount_minor": leg["goods_minor"],
            }
        ],
    )
    assert (
        db.scalar(select(func.sum(GrantUsage.amount_minor)).where(GrantUsage.grant_id == grant.id))
        == used_before
    )
    again = wallet_quote(
        rt, db, split_world, customer, f"wallet:envelope:{envelope.id}", items=[("a-rice", {})]
    )
    with pytest.raises(TrollieError) as err:
        execute_under_mandate(rt, agent_id=agent.id, quote_id=again.id)
    assert err.value.details["reason"] == "period_cap"


def test_w19_crash_after_merchant_accepted_before_local_record(rt, db, split_world):
    customer, wallet = funded(rt, db, amount=100_000)
    quote = wallet_quote(rt, db, split_world, customer, "wallet:unallocated")
    register_passkey(db, customer, rt.clock)
    approval = approve(db, customer, quote.id, rt.clock)
    order_id = create_order(rt, account_id=customer.account_id, approval_id=approval.id)
    # The commit step began (state and intent persisted), the merchant accepted leg 1, and
    # the process died before recording the result.
    from app.orders.service import _set_state
    from app.orders.state import LEG

    _set_state(rt, order_id, "COMMITTING")
    with tx(db):
        staged = db.scalars(
            select(OrderLeg).where(OrderLeg.order_id == order_id, OrderLeg.leg_id == "leg_1")
        ).one()
        LEG.move(staged, "COMMIT_REQUESTED")
    leg = db.scalars(
        select(OrderLeg).where(OrderLeg.order_id == order_id, OrderLeg.leg_id == "leg_1")
    ).one()
    from app.merchants.models import Reservation

    res = db.get(Reservation, leg.reservation_id)
    rt.merchant.commit_order(
        location_id=leg.location_id, client_ref=leg.commit_ref, reservation_ref=res.merchant_ref
    )
    pump(rt, rt.payments)  # restart: the step re-runs with the same reference
    assert state(db, order_id) == "FULFILLING"
    reservation = db.scalars(
        select(WalletReservation).where(WalletReservation.order_id == order_id)
    ).one()
    assert reservation.state == "committed" and reservation.amount_minor == quote.total_minor
    assert bal(db, wallet)["unallocated_minor"] == 100_000 - quote.total_minor


def test_wallet_balances_are_labelled_simulated(rt, db):
    customer, wallet = funded(rt, db, amount=1_234)
    b = bal(db, wallet)
    assert b["simulated"] is True and b["label"] == "SIMULATED — NOT REAL MONEY"
    assert b["total_minor"] == 1_234


def test_quote_funding_source_is_part_of_the_approved_snapshot(rt, db, split_world):
    customer, wallet = funded(rt, db)
    quote = wallet_quote(rt, db, split_world, customer, "wallet:unallocated")
    assert db.get(Quote, quote.id).snapshot["funding_source"] == "wallet:unallocated"

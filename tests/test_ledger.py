"""Ledger invariants (blueprint §7.3) and T52 (unbalanced posting pauses the money path)."""

import uuid

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.controls.models import Incident, KillSwitch
from app.controls.service import FINANCIAL, require_not_paused, set_kill_switch
from app.errors import ErrorCode, TrollieError
from app.ledger import chart
from app.ledger.models import LedgerEntry
from app.ledger.service import Leg, account, balance, credit, debit, post, reverse


def _accounts(db: Session) -> tuple[uuid.UUID, uuid.UUID]:
    wallet = uuid.uuid4()
    funds = account(db, chart.SIM_EXTERNAL_FUNDS, wallet)
    liability = account(db, chart.CUSTOMER_UNALLOCATED, wallet)
    return funds, liability


def test_balanced_posting_derives_balances(db: Session):
    funds, liability = _accounts(db)
    post(
        db,
        posting_key=f"topup:{uuid.uuid4()}",
        event_type="topup",
        legs=[debit(funds, 200_000), credit(liability, 200_000)],
    )
    db.commit()
    assert balance(db, funds) == 200_000
    assert balance(db, liability) == 200_000


def test_exact_replay_returns_same_transaction(db: Session):
    funds, liability = _accounts(db)
    key = f"topup:{uuid.uuid4()}"
    legs = [debit(funds, 5_000), credit(liability, 5_000)]
    first = post(db, posting_key=key, event_type="topup", legs=legs)
    db.commit()
    assert post(db, posting_key=key, event_type="topup", legs=legs) == first
    db.commit()
    assert balance(db, liability) == 5_000


def test_posting_key_reuse_with_different_entries_conflicts(db: Session):
    funds, liability = _accounts(db)
    key = f"topup:{uuid.uuid4()}"
    post(
        db,
        posting_key=key,
        event_type="topup",
        legs=[debit(funds, 5_000), credit(liability, 5_000)],
    )
    db.commit()
    with pytest.raises(TrollieError) as err:
        post(
            db,
            posting_key=key,
            event_type="topup",
            legs=[debit(funds, 6_000), credit(liability, 6_000)],
        )
    assert err.value.code is ErrorCode.DUPLICATE_OPERATION_CONFLICT


def test_t52_unbalanced_posting_rejected_paused_and_alerted(db: Session, engine: Engine):
    funds, liability = _accounts(db)
    db.commit()
    key = f"bad:{uuid.uuid4()}"
    with pytest.raises(TrollieError) as err:
        post(
            db,
            posting_key=key,
            event_type="topup",
            legs=[debit(funds, 5_000), credit(liability, 4_999)],
        )
    assert err.value.code is ErrorCode.LEDGER_INVARIANT_VIOLATION
    db.rollback()
    try:
        with pytest.raises(TrollieError) as paused:
            require_not_paused(db)
        assert paused.value.code is ErrorCode.FINANCIAL_ACTIONS_PAUSED
        incident = db.scalars(
            select(Incident).where(Incident.details["posting_key"].astext == key)
        ).one()
        assert incident.kind == "ledger_invariant_violation"
        assert balance(db, funds) == 0
    finally:
        db.rollback()
        with db.begin():
            set_kill_switch(db, FINANCIAL, False, reason="test cleanup", by="test")


@pytest.mark.parametrize(
    "legs",
    [
        [Leg(uuid.uuid4(), debit=1)],
        "zero",
        "both_sides",
        "float",
    ],
)
def test_malformed_postings_rejected(db: Session, engine: Engine, legs):
    funds, liability = _accounts(db)
    db.commit()
    match legs:
        case "zero":
            legs = [Leg(funds), Leg(liability)]
        case "both_sides":
            legs = [Leg(funds, debit=5, credit=5), Leg(liability, credit=0, debit=0)]
        case "float":
            legs = [Leg(funds, debit=1.5), Leg(liability, credit=1.5)]  # type: ignore[arg-type]
    try:
        with pytest.raises(TrollieError):
            post(db, posting_key=f"bad:{uuid.uuid4()}", event_type="x", legs=legs)
    finally:
        db.rollback()
        with db.begin():
            set_kill_switch(db, FINANCIAL, False, reason="test cleanup", by="test")


def _raw_transaction(db: Session, *amounts: tuple[uuid.UUID, int, int]) -> None:
    tid = uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO ledger_transactions (id, posting_key, entries_digest, event_type) "
            "VALUES (:id, :key, 'raw', 'raw')"
        ),
        {"id": tid, "key": f"raw:{tid}"},
    )
    for acct, dr, cr in amounts:
        db.execute(
            text(
                "INSERT INTO ledger_entries (transaction_id, account_id, currency, debit_minor,"
                " credit_minor) VALUES (:t, :a, 'ZAR', :d, :c)"
            ),
            {"t": tid, "a": acct, "d": dr, "c": cr},
        )


def test_database_rejects_unbalanced_transaction_at_commit(db: Session):
    """Bypassing the posting procedure still cannot commit an unbalanced transaction."""
    funds, liability = _accounts(db)
    db.commit()
    _raw_transaction(db, (funds, 100, 0), (liability, 0, 99))
    with pytest.raises(DBAPIError, match="unbalanced"):
        db.commit()
    db.rollback()


def test_database_rejects_single_entry_transaction(db: Session):
    funds, _ = _accounts(db)
    db.commit()
    _raw_transaction(db, (funds, 100, 0))
    with pytest.raises(DBAPIError, match="fewer than two"):
        db.commit()
    db.rollback()


def test_entries_cannot_be_added_to_posted_transaction(db: Session):
    funds, liability = _accounts(db)
    tid = post(
        db,
        posting_key=f"k:{uuid.uuid4()}",
        event_type="x",
        legs=[debit(funds, 10), credit(liability, 10)],
    )
    db.commit()
    with pytest.raises(DBAPIError, match="already posted"):
        db.add_all(
            [
                LedgerEntry(
                    transaction_id=tid,
                    account_id=funds,
                    currency="ZAR",
                    debit_minor=5,
                    credit_minor=0,
                ),
                LedgerEntry(
                    transaction_id=tid,
                    account_id=liability,
                    currency="ZAR",
                    debit_minor=0,
                    credit_minor=5,
                ),
            ]
        )
        db.flush()
    db.rollback()


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE ledger_entries SET debit_minor = debit_minor + 1 WHERE transaction_id = :t "
        "AND debit_minor > 0",
        "DELETE FROM ledger_entries WHERE transaction_id = :t",
        "UPDATE ledger_transactions SET event_type = 'edited' WHERE id = :t",
        "DELETE FROM ledger_transactions WHERE id = :t",
        "TRUNCATE ledger_entries",
    ],
)
def test_posted_rows_are_append_only(db: Session, statement: str):
    funds, liability = _accounts(db)
    tid = post(
        db,
        posting_key=f"k:{uuid.uuid4()}",
        event_type="x",
        legs=[debit(funds, 10), credit(liability, 10)],
    )
    db.commit()
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text(statement), {"t": tid})
    db.rollback()


def test_currency_must_match_account(db: Session):
    funds, liability = _accounts(db)
    db.commit()
    tid = post(
        db,
        posting_key=f"k:{uuid.uuid4()}",
        event_type="x",
        legs=[debit(funds, 10), credit(liability, 10)],
    )
    with pytest.raises(IntegrityError):
        db.execute(
            text(
                "INSERT INTO ledger_entries (transaction_id, account_id, currency, debit_minor,"
                " credit_minor) VALUES (:t, :a, 'USD', 1, 0)"
            ),
            {"t": tid, "a": funds},
        )
    db.rollback()


def test_reversal_restores_balances_and_happens_once(db: Session):
    funds, liability = _accounts(db)
    tid = post(
        db,
        posting_key=f"k:{uuid.uuid4()}",
        event_type="topup",
        legs=[debit(funds, 700), credit(liability, 700)],
    )
    reverse(db, tid, posting_key=f"rev:{tid}")
    db.commit()
    assert balance(db, funds) == 0 and balance(db, liability) == 0
    with pytest.raises(IntegrityError):
        reverse(db, tid, posting_key=f"rev2:{tid}")
    db.rollback()


def test_platform_accounts_are_unique_without_owner(db: Session):
    a = account(db, chart.OPERATING_RESERVE, None)
    b = account(db, chart.OPERATING_RESERVE, None)
    db.commit()
    assert a == b


amounts = st.integers(min_value=1, max_value=10_000_000)


@settings(
    max_examples=40, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    postings=st.lists(
        st.tuples(
            st.lists(st.tuples(st.integers(0, 3), amounts), min_size=1, max_size=4),
            st.integers(0, 3),
        ),
        min_size=1,
        max_size=8,
    )
)
def test_property_ledger_always_balances(db: Session, postings):
    """Any sequence of balanced postings keeps every transaction and the whole set balanced,
    and derived balances equal an independent running model."""
    owner = uuid.uuid4()
    accts = [
        account(db, t, owner)
        for t in (
            chart.SIM_EXTERNAL_FUNDS,
            chart.CUSTOMER_UNALLOCATED,
            chart.ENVELOPE_AVAILABLE,
            chart.PURCHASE_RESERVED,
        )
    ]
    model = dict.fromkeys(accts, 0)  # debit minus credit
    for i, (debits, credit_idx) in enumerate(postings):
        legs = [debit(accts[a], amt) for a, amt in debits]
        legs.append(credit(accts[credit_idx], sum(amt for _, amt in debits)))
        post(db, posting_key=f"p:{owner}:{i}", event_type="prop", legs=legs)
        for leg in legs:
            model[leg.account_id] += leg.debit - leg.credit
    db.commit()
    net = db.execute(
        select(func.sum(LedgerEntry.debit_minor) - func.sum(LedgerEntry.credit_minor)).where(
            LedgerEntry.account_id.in_(accts)
        )
    ).scalar_one()
    assert net == 0
    for acct in accts:
        signed = balance(db, acct)
        is_debit_normal = acct == accts[0]
        assert (signed if is_debit_normal else -signed) == model[acct]


def test_kill_switch_does_not_block_ledger_postings(db: Session):
    """Refunds and reconciliation keep posting while new commitments are paused."""
    funds, liability = _accounts(db)
    db.commit()
    with db.begin():
        set_kill_switch(db, "test-scope", True, reason="test", by="test")
    try:
        post(
            db,
            posting_key=f"k:{uuid.uuid4()}",
            event_type="refund",
            legs=[debit(liability, 10), credit(funds, 10)],
        )
        db.commit()
    finally:
        with db.begin():
            set_kill_switch(db, "test-scope", False, reason="cleanup", by="test")
    assert db.get(KillSwitch, "test-scope").engaged is False

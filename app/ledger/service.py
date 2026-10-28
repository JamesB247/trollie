"""Posting procedure. The only path by which application code writes ledger rows.

Database triggers (migration 0002) enforce the same invariants independently:
balanced per currency at commit, at least two entries, append-only, and no entries
added to a transaction after the database transaction that created it.
"""

import hashlib
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import Engine, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.controls.service import FINANCIAL, raise_incident_and_pause
from app.errors import ErrorCode, TrollieError
from app.ledger.chart import AccountType
from app.ledger.models import AccountClass, LedgerAccount, LedgerEntry, LedgerTransaction


@dataclass(frozen=True)
class Leg:
    """One side of a posting. Exactly one of debit/credit is positive."""

    account_id: uuid.UUID
    debit: int = 0
    credit: int = 0


def debit(account_id: uuid.UUID, amount: int) -> Leg:
    return Leg(account_id, debit=amount)


def credit(account_id: uuid.UUID, amount: int) -> Leg:
    return Leg(account_id, credit=amount)


def account(
    session: Session, kind: AccountType, owner_id: uuid.UUID | None, currency: str = "ZAR"
) -> uuid.UUID:
    """Get or create the account for (type, owner, currency). Safe under concurrency."""
    stmt = (
        insert(LedgerAccount)
        .values(
            id=uuid.uuid4(),
            code=kind.code,
            owner_type=kind.owner_type,
            owner_id=owner_id,
            currency=currency,
            account_class=kind.account_class,
        )
        .on_conflict_do_nothing(constraint="uq_ledger_accounts_natural_key")
    )
    session.execute(stmt)
    owner_clause = (
        LedgerAccount.owner_id.is_(None) if owner_id is None else LedgerAccount.owner_id == owner_id
    )
    return session.scalars(
        select(LedgerAccount.id).where(
            LedgerAccount.code == kind.code,
            LedgerAccount.owner_type == kind.owner_type,
            owner_clause,
            LedgerAccount.currency == currency,
        )
    ).one()


def _digest(event_type: str, legs: list[Leg], reverses_id: uuid.UUID | None) -> str:
    canonical = json.dumps(
        {
            "event_type": event_type,
            "reverses": str(reverses_id) if reverses_id else None,
            "legs": sorted([str(x.account_id), x.debit, x.credit] for x in legs),
        },
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _violation(engine: Engine | None, posting_key: str, reason: str) -> TrollieError:
    if engine is not None:
        # T52: an unbalanced posting pauses the money path and alerts.
        raise_incident_and_pause(
            engine,
            kind="ledger_invariant_violation",
            scope=FINANCIAL,
            posting_key=posting_key,
            reason=reason,
        )
    return TrollieError(ErrorCode.LEDGER_INVARIANT_VIOLATION, reason, posting_key=posting_key)


def post(
    session: Session,
    *,
    posting_key: str,
    event_type: str,
    legs: list[Leg],
    business_operation_id: uuid.UUID | None = None,
    reverses_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Post a balanced transaction, or return the existing one for an exact replay."""
    engine = session.get_bind() if isinstance(session.get_bind(), Engine) else None
    if len(legs) < 2:
        raise _violation(engine, posting_key, "a transaction needs at least two entries")
    for leg in legs:
        if not isinstance(leg.debit, int) or not isinstance(leg.credit, int):
            raise _violation(engine, posting_key, "amounts must be integer minor units")
        if not ((leg.debit > 0) ^ (leg.credit > 0)) or min(leg.debit, leg.credit) < 0:
            raise _violation(engine, posting_key, "each entry needs exactly one positive side")

    accounts = {
        row.id: row
        for row in session.scalars(
            select(LedgerAccount).where(LedgerAccount.id.in_({x.account_id for x in legs}))
        )
    }
    if len(accounts) != len({x.account_id for x in legs}):
        raise _violation(engine, posting_key, "unknown ledger account")
    totals: dict[str, int] = defaultdict(int)
    for leg in legs:
        totals[accounts[leg.account_id].currency] += leg.debit - leg.credit
    if any(totals.values()):
        raise _violation(engine, posting_key, f"unbalanced posting {dict(totals)}")

    digest = _digest(event_type, legs, reverses_id)
    existing = session.scalars(
        select(LedgerTransaction).where(LedgerTransaction.posting_key == posting_key)
    ).one_or_none()
    if existing is not None:
        if existing.entries_digest != digest:
            raise TrollieError(
                ErrorCode.DUPLICATE_OPERATION_CONFLICT,
                "posting key reused with different entries",
                posting_key=posting_key,
            )
        return existing.id

    txn = LedgerTransaction(
        id=uuid.uuid4(),
        posting_key=posting_key,
        entries_digest=digest,
        event_type=event_type,
        business_operation_id=business_operation_id,
        reverses_id=reverses_id,
    )
    session.add(txn)
    session.flush()
    session.add_all(
        LedgerEntry(
            transaction_id=txn.id,
            account_id=leg.account_id,
            currency=accounts[leg.account_id].currency,
            debit_minor=leg.debit,
            credit_minor=leg.credit,
        )
        for leg in legs
    )
    session.flush()
    return txn.id


def reverse(session: Session, transaction_id: uuid.UUID, *, posting_key: str) -> uuid.UUID:
    """Post the exact opposite of a transaction. A transaction can be reversed once."""
    original = session.get(LedgerTransaction, transaction_id)
    if original is None:
        raise TrollieError(ErrorCode.NOT_FOUND, "ledger transaction not found")
    entries = session.scalars(
        select(LedgerEntry).where(LedgerEntry.transaction_id == transaction_id)
    ).all()
    legs = [Leg(e.account_id, debit=e.credit_minor, credit=e.debit_minor) for e in entries]
    return post(
        session,
        posting_key=posting_key,
        event_type=f"reversal:{original.event_type}",
        legs=legs,
        business_operation_id=original.business_operation_id,
        reverses_id=original.id,
    )


def balance(session: Session, account_id: uuid.UUID) -> int:
    """Balance on the account's normal side, derived from entries."""
    acct = session.get(LedgerAccount, account_id)
    if acct is None:
        raise TrollieError(ErrorCode.NOT_FOUND, "ledger account not found")
    debits, credits = session.execute(
        select(
            func.coalesce(func.sum(LedgerEntry.debit_minor), 0),
            func.coalesce(func.sum(LedgerEntry.credit_minor), 0),
        ).where(LedgerEntry.account_id == account_id)
    ).one()
    net = int(debits) - int(credits)
    return net if AccountClass(acct.account_class).debit_normal else -net


def lock_accounts(session: Session, account_ids: list[uuid.UUID]) -> None:
    """Serialise balance checks on these accounts for the rest of the transaction."""
    session.execute(
        select(LedgerAccount.id)
        .where(LedgerAccount.id.in_(account_ids))
        .order_by(LedgerAccount.id)
        .with_for_update()
    ).all()

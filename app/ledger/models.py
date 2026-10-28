import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, created_at, uuid_pk


class AccountClass(StrEnum):
    ASSET = "asset"
    LIABILITY = "liability"
    REVENUE = "revenue"
    EXPENSE = "expense"
    EQUITY = "equity"

    @property
    def debit_normal(self) -> bool:
        return self in (AccountClass.ASSET, AccountClass.EXPENSE)


class LedgerAccount(Base):
    """An operational control account. Meaning of each code is in app/ledger/chart.py."""

    __tablename__ = "ledger_accounts"
    __table_args__ = (
        UniqueConstraint(
            "code",
            "owner_type",
            "owner_id",
            "currency",
            name="uq_ledger_accounts_natural_key",
            postgresql_nulls_not_distinct=True,
        ),
        UniqueConstraint("id", "currency", name="uq_ledger_accounts_id_currency"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(Text)
    owner_type: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID | None]
    currency: Mapped[str] = mapped_column(String(3))
    account_class: Mapped[AccountClass] = mapped_column(
        Enum(AccountClass, name="account_class", values_callable=lambda e: [m.value for m in e])
    )
    created_at: Mapped[datetime] = created_at()


class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    id: Mapped[uuid.UUID] = uuid_pk()
    # Identifies the economic event; a second posting of the same event is a replay or a conflict.
    posting_key: Mapped[str] = mapped_column(Text, unique=True)
    entries_digest: Mapped[str] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(Text)
    business_operation_id: Mapped[uuid.UUID | None]
    reverses_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ledger_transactions.id"), unique=True
    )
    # Entries may only be added in the database transaction that created this row.
    posted_txid: Mapped[int] = mapped_column(server_default=func.txid_current())
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint(
            "(debit_minor > 0 AND credit_minor = 0) OR (credit_minor > 0 AND debit_minor = 0)",
            name="one_side_positive",
        ),
        ForeignKeyConstraint(
            ["account_id", "currency"],
            ["ledger_accounts.id", "ledger_accounts.currency"],
            name="fk_ledger_entries_account_currency",
        ),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ledger_transactions.id"), index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(index=True)
    currency: Mapped[str] = mapped_column(String(3))
    debit_minor: Mapped[int] = mapped_column(default=0)
    credit_minor: Mapped[int] = mapped_column(default=0)

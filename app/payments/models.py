import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, created_at, uuid_pk


class Action(StrEnum):
    AUTHORISE = "authorise"
    CAPTURE = "capture"
    CHARGE = "charge"  # immediate-payment rail
    VOID = "void"
    REFUND = "refund"


class OpState(StrEnum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED_FINAL = "FAILED_FINAL"
    UNKNOWN = "UNKNOWN"
    RECONCILING = "RECONCILING"


class FinancialOperation(Base):
    """One intended economic operation with its own lifecycle (blueprint §8.3).

    The idempotency key is derived from the business operation and never regenerated,
    so a user pressing Buy again replays the same operation (CLAUDE.md rules).
    """

    __tablename__ = "financial_operations"
    __table_args__ = (CheckConstraint("amount_minor > 0", name="amount_positive"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    order_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    subject_type: Mapped[str] = mapped_column(Text, default="order")
    action: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text)
    profile_key: Mapped[str] = mapped_column(Text)
    profile_version: Mapped[int]
    amount_minor: Mapped[int]
    currency: Mapped[str] = mapped_column(Text, default="ZAR")
    idempotency_key: Mapped[str] = mapped_column(Text, unique=True)
    request_hash: Mapped[str] = mapped_column(Text)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("financial_operations.id"))
    state: Mapped[str] = mapped_column(Text, default=OpState.CREATED)
    external_ref: Mapped[str | None] = mapped_column(Text, index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Exact non-amount request arguments, kept so a safe same-key replay is identical.
    request_args: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    last_observation: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = created_at()


class PaymentAllocation(Base):
    """Economic owner of each part of a charge. Allocation is not proof of settlement."""

    __tablename__ = "payment_allocations"

    id: Mapped[uuid.UUID] = uuid_pk()
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("financial_operations.id"), index=True
    )
    party_type: Mapped[str] = mapped_column(Text)  # merchant | courier | platform
    party_id: Mapped[uuid.UUID | None]
    provider_beneficiary: Mapped[str] = mapped_column(Text)
    gross_minor: Mapped[int]
    fee_minor: Mapped[int | None]
    net_minor: Mapped[int | None]


class RefundState(StrEnum):
    REQUESTED = "REQUESTED"
    ASSESSED = "ASSESSED"
    APPROVED = "APPROVED"
    SUBMITTED = "SUBMITTED"
    PROVIDER_CONFIRMED = "PROVIDER_CONFIRMED"
    PENDING = "PENDING"
    UNKNOWN = "UNKNOWN"
    REJECTED_WITH_REASON = "REJECTED_WITH_REASON"
    FAILED_REQUIRES_ACTION = "FAILED_REQUIRES_ACTION"


class Refund(Base):
    """Refund case (blueprint §8.4, §14.5). Customer entitlement, provider reversal and
    merchant liability are tracked separately (T32)."""

    __tablename__ = "refunds"
    __table_args__ = (CheckConstraint("amount_minor > 0", name="amount_positive"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(index=True)
    business_key: Mapped[str] = mapped_column(Text, unique=True)
    original_operation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("financial_operations.id"))
    operation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("financial_operations.id"))
    reason: Mapped[str] = mapped_column(Text)
    amount_minor: Mapped[int]
    economic_allocation: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    provider_allocation: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(Text, default=RefundState.REQUESTED)
    destination: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = created_at()


class SettlementReport(Base):
    __tablename__ = "settlement_reports"

    id: Mapped[uuid.UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(Text)
    report_ref: Mapped[str] = mapped_column(Text, unique=True)
    content_hash: Mapped[str] = mapped_column(Text)
    imported_at: Mapped[datetime] = created_at()


class SettlementItem(Base):
    __tablename__ = "settlement_items"
    __table_args__ = (
        UniqueConstraint("report_id", "line_no"),
        # One provider settlement line can never be imported twice (blueprint §7.3; T53).
        UniqueConstraint("provider_line_ref"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("settlement_reports.id"))
    line_no: Mapped[int]
    provider_line_ref: Mapped[str] = mapped_column(Text)
    operation_ref: Mapped[str] = mapped_column(Text)
    beneficiary: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)  # payout | fee | payout_failed
    gross_minor: Mapped[int]
    fee_minor: Mapped[int]
    net_minor: Mapped[int]
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

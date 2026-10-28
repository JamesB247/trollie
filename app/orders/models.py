import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, created_at, uuid_pk


class Order(Base):
    """Parent purchase. One execution per approval (unique), so parallel requests from the
    same approval produce one logical purchase (T24)."""

    __tablename__ = "orders"
    __table_args__ = (
        # Exactly one authority: a quote-bound approval or a mandate execution (A2).
        CheckConstraint(
            "num_nonnulls(approval_id, mandate_execution_id) = 1", name="one_authority"
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_accounts.id"), index=True)
    quote_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quotes.id"), unique=True)
    approval_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("approvals.id"), unique=True)
    mandate_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mandate_executions.id"), unique=True
    )
    approved_hash: Mapped[str] = mapped_column(Text)
    execution_snapshot_hash: Mapped[str] = mapped_column(Text)
    funding_source: Mapped[str] = mapped_column(Text)
    profile_key: Mapped[str] = mapped_column(Text)
    address_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("address_versions.id"))
    state: Mapped[str] = mapped_column(Text, default="CREATED")
    attention_reason: Mapped[str | None] = mapped_column(Text)
    # Chosen outcome when not every leg is fulfilled: full | partial | cancel_all.
    plan: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    customer_cancel_requested: Mapped[bool] = mapped_column(default=False)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = created_at()


class OrderLeg(Base):
    __tablename__ = "order_legs"
    __table_args__ = (UniqueConstraint("order_id", "leg_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    leg_id: Mapped[str] = mapped_column(Text)
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchants.id"))
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchant_locations.id"))
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reservations.id"))
    # Server-generated business reference; the merchant deduplicates on it.
    commit_ref: Mapped[str] = mapped_column(Text, unique=True)
    merchant_ref: Mapped[str | None] = mapped_column(Text)
    goods_minor: Mapped[int]
    delivery_minor: Mapped[int]
    line_ids: Mapped[list[str]] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(Text, default="RESERVED")
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = created_at()


class DeliveryJob(Base):
    __tablename__ = "delivery_jobs"

    id: Mapped[uuid.UUID] = uuid_pk()
    order_leg_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("order_legs.id"), unique=True)
    slot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("delivery_slots.id"))
    courier_code: Mapped[str] = mapped_column(Text)
    booking_ref: Mapped[str] = mapped_column(Text, unique=True)
    courier_ref: Mapped[str | None] = mapped_column(Text)
    # Delivery only to the approved, immutable address version (T42).
    address_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("address_versions.id"))
    state: Mapped[str] = mapped_column(Text, default="QUOTED")
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = created_at()

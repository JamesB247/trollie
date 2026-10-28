import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, created_at, uuid_pk


class FulfilmentMode(StrEnum):
    COMPLETE_REQUIRED = "complete_required"
    ALLOW_PARTIAL = "allow_partial"


class ShoppingSession(Base):
    __tablename__ = "shopping_sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_accounts.id"), index=True)
    address_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("address_versions.id"))
    budget_minor: Mapped[int | None]
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, default="open")
    created_at: Mapped[datetime] = created_at()


class RequestedItem(Base):
    """A structured request. Agents may propose these, referencing existing product ids only."""

    __tablename__ = "requested_items"
    __table_args__ = (
        UniqueConstraint("session_id", "line_id"),
        CheckConstraint(
            "(quantity_packs IS NOT NULL) <> (quantity_measure IS NOT NULL)", name="one_quantity"
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shopping_sessions.id"), index=True)
    line_id: Mapped[str] = mapped_column(Text)
    rule: Mapped[str] = mapped_column(Text)
    candidates: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    quantity_packs: Mapped[int | None]
    quantity_measure: Mapped[int | None]
    quantity_unit: Mapped[str | None] = mapped_column(Text)
    must_have: Mapped[bool] = mapped_column(default=False)
    # Set when the source could not establish quantity or identity unambiguously (T02, T03).
    needs_clarification: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()


class QuoteKind(StrEnum):
    ESTIMATE = "estimate"  # unreserved; never purchasable
    FIRM = "firm"  # every leg has a held reservation until expires_at


class QuoteState(StrEnum):
    ESTIMATE = "ESTIMATE"
    FIRM = "FIRM"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    CONSUMED = "CONSUMED"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"
    REPLACED = "REPLACED"


class Quote(Base):
    """Immutable quote snapshot. Only `state`/`state_version` may change (DB trigger)."""

    __tablename__ = "quotes"
    __table_args__ = (UniqueConstraint("session_id", "version"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shopping_sessions.id"), index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_accounts.id"), index=True)
    version: Mapped[int]
    kind: Mapped[str] = mapped_column(Text)
    strategy: Mapped[str] = mapped_column(Text)
    derived_from_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("quotes.id"))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    quote_hash: Mapped[str] = mapped_column(Text, unique=True)
    total_minor: Mapped[int]
    maximum_payable_minor: Mapped[int]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(Text)
    state_version: Mapped[int] = mapped_column(default=1)
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("quotes.id"))
    created_at: Mapped[datetime] = created_at()


class QuoteLeg(Base):
    __tablename__ = "quote_legs"
    __table_args__ = (UniqueConstraint("quote_id", "leg_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    quote_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quotes.id"), index=True)
    leg_id: Mapped[str] = mapped_column(Text)
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchants.id"))
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchant_locations.id"))
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reservations.id"))
    slot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("delivery_slots.id"))
    goods_minor: Mapped[int]
    delivery_minor: Mapped[int]

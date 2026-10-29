import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, created_at, uuid_pk


class MerchantState(StrEnum):
    """PRD merchant states. Only PAYMENT_ENABLED merchants can receive orders."""

    DRAFT = "draft"
    INTEGRATION_TESTED = "integration_tested"
    VERIFICATION_PENDING = "verification_pending"
    PAYMENT_ENABLED = "payment_enabled"
    SUSPENDED = "suspended"
    EXITED = "exited"


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(Text, unique=True)
    display_name: Mapped[str] = mapped_column(Text)
    legal_name: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text, default=MerchantState.DRAFT)
    synthetic: Mapped[bool] = mapped_column(default=True)
    # Payout destination is a versioned reference; nothing merchant-supplied can change it.
    payout_destination_version: Mapped[str | None] = mapped_column(Text)
    # "probation" for newly onboarded merchants: onboarding checks (KYB) can be fooled, so
    # exposure is limited until the merchant has a delivery record (crowd simulation).
    risk_tier: Mapped[str] = mapped_column(Text, default="standard", server_default="standard")
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()


class MerchantLocation(Base):
    __tablename__ = "merchant_locations"

    id: Mapped[uuid.UUID] = uuid_pk()
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    service_zones: Mapped[list[str]] = mapped_column(ARRAY(Text))
    minimum_order_minor: Mapped[int] = mapped_column(default=0)
    pick_minutes: Mapped[int] = mapped_column(default=45)
    created_at: Mapped[datetime] = created_at()


class MerchantCapability(Base):
    """Versioned, evidence-backed capability flags. Never inferred from a platform label."""

    __tablename__ = "merchant_capabilities"
    __table_args__ = (UniqueConstraint("location_id", "version"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchant_locations.id"))
    version: Mapped[int]
    can_reserve: Mapped[bool]
    can_commit: Mapped[bool]
    can_cancel: Mapped[bool]
    can_lookup_by_reference: Mapped[bool]
    reservation_ttl_seconds: Mapped[int]
    evidence: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()


class ReservationState(StrEnum):
    REQUESTED = "REQUESTED"
    HELD = "HELD"
    CONSUMED = "CONSUMED"
    RELEASE_REQUESTED = "RELEASE_REQUESTED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class Reservation(Base):
    """Trollie's record of a merchant stock/price hold (blueprint §2.5, §8.1).

    Release or expiry of a hold is not cancellation of a sale. UNKNOWN is resolved by
    lookup on `client_ref`, never by a second reservation with a new reference.
    """

    __tablename__ = "reservations"

    id: Mapped[uuid.UUID] = uuid_pk()
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchant_locations.id"), index=True)
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchants.id"))
    client_ref: Mapped[str] = mapped_column(Text, unique=True)
    lines: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    lines_hash: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text, default=ReservationState.REQUESTED)
    merchant_ref: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = created_at()

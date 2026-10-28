import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
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

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, created_at, uuid_pk


class TaxCode(StrEnum):
    STANDARD = "standard"
    ZERO_RATED = "zero_rated"


class StockConfidence(StrEnum):
    """How much the stock observation can be trusted. Only a reservation is a hold (T07)."""

    CONFIRMED = "confirmed"
    OBSERVED = "observed"
    LOW = "low"
    UNKNOWN = "unknown"


class OfferVersion(Base):
    """Immutable price/stock observation for one product at one location.

    The latest observation per (location, product) is current. Prices are VAT-inclusive
    integer cents; tax_code is kept for invoices only and never added again (T13).
    """

    __tablename__ = "offer_versions"
    __table_args__ = (
        CheckConstraint("price_minor > 0", name="price_positive"),
        CheckConstraint("stock_quantity IS NULL OR stock_quantity >= 0", name="stock_nonneg"),
        Index("ix_offer_versions_current", "location_id", "product_id", "observed_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchant_locations.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    merchant_sku: Mapped[str] = mapped_column(Text)
    price_minor: Mapped[int]
    tax_code: Mapped[str] = mapped_column(Text)
    stock_quantity: Mapped[int | None]
    stock_confidence: Mapped[str] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Untrusted merchant-supplied text. Displayed as data; never parsed for instructions (T45).
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = created_at()


class PromotionKind(StrEnum):
    FIXED_LINE = "fixed_line"  # benefit_minor off each qualifying unit
    PERCENT_LINE = "percent_line"  # percent_bp basis points off each qualifying unit
    MULTIBUY = "multibuy"  # min_quantity units of one product for bundle_price_minor
    DELIVERY_THRESHOLD = "delivery_threshold"  # free delivery at min_spend_minor goods
    LOYALTY_PRICE = "loyalty_price"  # price_minor for verified loyalty members only


class Promotion(Base):
    """Structured promotion rule (DECISIONS.md D-S03.3). Non-stacking unless stackable."""

    __tablename__ = "promotions"

    id: Mapped[uuid.UUID] = uuid_pk()
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchant_locations.id"))
    version: Mapped[int] = mapped_column(default=1)
    kind: Mapped[str] = mapped_column(Text)
    product_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    min_quantity: Mapped[int] = mapped_column(default=1)
    min_spend_minor: Mapped[int] = mapped_column(default=0)
    benefit_minor: Mapped[int] = mapped_column(default=0)
    percent_bp: Mapped[int] = mapped_column(default=0)
    bundle_price_minor: Mapped[int | None]
    price_minor: Mapped[int | None]
    requires_loyalty_programme: Mapped[str | None] = mapped_column(Text)
    stackable: Mapped[bool] = mapped_column(default=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()

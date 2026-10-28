import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, Index, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, created_at, uuid_pk


class Unit(StrEnum):
    ML = "ml"
    G = "g"
    EACH = "each"


class Product(Base):
    """Canonical product identity, independent of any store's offer."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = uuid_pk()
    gtin: Mapped[str | None] = mapped_column(Text, unique=True)
    brand: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    variant: Mapped[str] = mapped_column(Text, default="")
    # Declared quantity of one sellable unit: e.g. 1000 ml, or 6 x 1000 ml for a multipack.
    unit_measure: Mapped[int]
    unit: Mapped[str] = mapped_column(Text)
    pack_count: Mapped[int] = mapped_column(default=1)
    category: Mapped[str] = mapped_column(Text)
    ambient: Mapped[bool] = mapped_column(default=True)
    regulated: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = created_at()

    @property
    def total_measure(self) -> int:
        return self.unit_measure * self.pack_count


class MatchLevel(StrEnum):
    """Matching hierarchy (blueprint §11.1). Only the first four make an offer orderable."""

    GTIN_VERIFIED = "gtin_verified"
    MAPPING_VERIFIED = "mapping_verified"
    ATTRIBUTES_REVIEWED = "attributes_reviewed"
    USER_CONFIRMED = "user_confirmed"
    SUGGESTED = "suggested"


ORDERABLE_MATCH_LEVELS = (
    MatchLevel.GTIN_VERIFIED,
    MatchLevel.MAPPING_VERIFIED,
    MatchLevel.ATTRIBUTES_REVIEWED,
    MatchLevel.USER_CONFIRMED,
)


class ProductMapping(Base):
    """Merchant SKU → canonical product, with auditable revisions."""

    __tablename__ = "product_mappings"
    __table_args__ = (
        UniqueConstraint("merchant_id", "merchant_sku", "revision"),
        Index(
            "uq_product_mappings_active_sku",
            "merchant_id",
            "merchant_sku",
            unique=True,
            postgresql_where=text("active"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchants.id"))
    merchant_sku: Mapped[str] = mapped_column(Text)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    revision: Mapped[int] = mapped_column(default=1)
    match_level: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = created_at()


def gtin_is_valid(gtin: str) -> bool:
    """GS1 check-digit validation for GTIN-8/12/13/14."""
    if not gtin.isdigit() or len(gtin) not in (8, 12, 13, 14):
        return False
    digits = [int(c) for c in gtin]
    body, check = digits[:-1], digits[-1]
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - total % 10) % 10 == check

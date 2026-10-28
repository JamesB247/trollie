import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, created_at, uuid_pk


class CustomerAccount(Base):
    """One adult owner per pilot account. A phone number is not proof of identity (T23)."""

    __tablename__ = "customer_accounts"

    id: Mapped[uuid.UUID] = uuid_pk()
    display_name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="active")
    created_at: Mapped[datetime] = created_at()


class AddressVersion(Base):
    """Immutable, encrypted address version. Approvals bind to a version, not a pointer (T19)."""

    __tablename__ = "address_versions"
    __table_args__ = (UniqueConstraint("account_id", "label", "version"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_accounts.id"), index=True)
    label: Mapped[str] = mapped_column(Text)
    version: Mapped[int]
    key_id: Mapped[str] = mapped_column(Text)
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    # Non-sensitive routing attribute used by the optimiser.
    service_zone: Mapped[str] = mapped_column(Text)
    validated: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = created_at()


class LoyaltyMembership(Base):
    __tablename__ = "loyalty_memberships"
    __table_args__ = (UniqueConstraint("account_id", "programme"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_accounts.id"))
    programme: Mapped[str] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()

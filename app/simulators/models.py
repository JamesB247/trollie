"""State owned by the simulated external parties. Trollie code never reads these directly;
it only sees what the adapters return."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, created_at, uuid_pk


class SimFault(Base):
    """Injected failure: the next `remaining` calls of `operation` at `target` misbehave."""

    __tablename__ = "sim_faults"

    id: Mapped[uuid.UUID] = uuid_pk()
    system: Mapped[str] = mapped_column(Text)  # merchant | payment | courier
    target: Mapped[str] = mapped_column(Text)  # location id, provider account, courier code
    operation: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(Text)
    remaining: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = created_at()


class SimMerchantStock(Base):
    __tablename__ = "sim_merchant_stock"

    location_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    product_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    on_hand: Mapped[int]
    held: Mapped[int] = mapped_column(default=0)


class SimMerchantReservation(Base):
    __tablename__ = "sim_merchant_reservations"

    client_ref: Mapped[str] = mapped_column(Text, primary_key=True)
    merchant_ref: Mapped[str] = mapped_column(Text, unique=True)
    location_id: Mapped[uuid.UUID]
    lines: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SimMerchantOrder(Base):
    __tablename__ = "sim_merchant_orders"

    client_ref: Mapped[str] = mapped_column(Text, primary_key=True)
    merchant_ref: Mapped[str] = mapped_column(Text, unique=True)
    location_id: Mapped[uuid.UUID]
    reservation_ref: Mapped[str] = mapped_column(Text)
    lines: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)

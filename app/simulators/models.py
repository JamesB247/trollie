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


class SimPayment(Base):
    __tablename__ = "sim_payments"

    provider_ref: Mapped[str] = mapped_column(Text, primary_key=True)
    # Merchant-side reference echoed in every event, as real providers do.
    client_key: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    collection: Mapped[str | None] = mapped_column(Text)
    reference: Mapped[str | None] = mapped_column(Text)
    amount_minor: Mapped[int]
    status: Mapped[str] = mapped_column(Text)
    parent_ref: Mapped[str | None] = mapped_column(Text)
    beneficiaries: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    captured_minor: Mapped[int] = mapped_column(default=0)
    refunded_minor: Mapped[int] = mapped_column(default=0)
    settled: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SimIdempotencyKey(Base):
    __tablename__ = "sim_payment_idempotency"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    request_hash: Mapped[str] = mapped_column(Text)
    provider_ref: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SimWebhook(Base):
    __tablename__ = "sim_webhooks"

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    deliver_after: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deliveries_remaining: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = created_at()


class SimCourierBooking(Base):
    __tablename__ = "sim_courier_bookings"

    booking_ref: Mapped[str] = mapped_column(Text, primary_key=True)
    courier_ref: Mapped[str] = mapped_column(Text, unique=True)
    slot_id: Mapped[uuid.UUID]
    location_id: Mapped[uuid.UUID]
    address_version_id: Mapped[uuid.UUID]
    state: Mapped[str] = mapped_column(Text)


class SimMerchantLatency(Base):
    """How slow a simulated merchant integration is, and how long Trollie waits for it."""

    __tablename__ = "sim_merchant_latency"

    location_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    mean_ms: Mapped[int]
    jitter_ms: Mapped[int]
    slow_permille: Mapped[int]  # share of calls that take slow_ms instead
    slow_ms: Mapped[int]
    timeout_ms: Mapped[int]  # Trollie's adapter budget; beyond it the call times out

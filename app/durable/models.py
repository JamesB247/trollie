import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, created_at, uuid_pk


class IdempotencyRecord(Base):
    """A business operation keyed by caller-supplied idempotency key (blueprint §10.5)."""

    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("scope", "key"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    scope: Mapped[str] = mapped_column(Text)
    key: Mapped[str] = mapped_column(Text)
    request_hash: Mapped[str] = mapped_column(Text)
    completed: Mapped[bool] = mapped_column(default=False)
    response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at()


class OutboxEvent(Base):
    __tablename__ = "event_outbox"
    __table_args__ = (
        Index(
            "ix_event_outbox_unpublished",
            "created_at",
            postgresql_where=text("published_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    aggregate_type: Mapped[str] = mapped_column(Text)
    aggregate_id: Mapped[uuid.UUID]
    aggregate_version: Mapped[int]
    event_type: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at()
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InboxState(StrEnum):
    RECEIVED = "received"
    PROCESSED = "processed"
    QUARANTINED = "quarantined"


class InboxEvent(Base):
    """A verified external event. Identity is unique per provider/account/environment."""

    __tablename__ = "event_inbox"
    __table_args__ = (UniqueConstraint("provider", "provider_account", "environment", "event_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(Text)
    provider_account: Mapped[str] = mapped_column(Text)
    environment: Mapped[str] = mapped_column(Text)
    event_id: Mapped[str] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(Text)
    payload_hash: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(Text, default=InboxState.RECEIVED)
    error: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = created_at()


class RejectedEvent(Base):
    """Events that failed verification or conflicted with a known event. Never processed."""

    __tablename__ = "event_rejections"

    id: Mapped[uuid.UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    event_id: Mapped[str | None] = mapped_column(Text)
    body_hash: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = created_at()


class JobState(StrEnum):
    READY = "ready"
    LEASED = "leased"
    DONE = "done"
    DEAD = "dead"


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index(
            "ix_jobs_claimable", "kind", "available_at", postgresql_where=text("state = 'ready'")
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    kind: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    dedupe_key: Mapped[str | None] = mapped_column(Text, unique=True)
    state: Mapped[str] = mapped_column(Text, default=JobState.READY)
    attempts: Mapped[int] = mapped_column(default=0)
    max_attempts: Mapped[int] = mapped_column(default=8)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[str | None] = mapped_column(Text)
    lease_token: Mapped[uuid.UUID | None]
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()

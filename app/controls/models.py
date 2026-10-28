import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, created_at, uuid_pk


class KillSwitch(Base):
    """Stops new economic commitments in a scope; never stops refunds or reconciliation."""

    __tablename__ = "kill_switches"

    scope: Mapped[str] = mapped_column(Text, primary_key=True)
    engaged: Mapped[bool] = mapped_column(default=False)
    reason: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[str] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = uuid_pk()
    kind: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = created_at()


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    actor: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    object_type: Mapped[str] = mapped_column(Text)
    object_id: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = created_at()

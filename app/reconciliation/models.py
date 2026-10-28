import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, created_at, uuid_pk


class ReconciliationCase(Base):
    """An owned, ageing exception (blueprint §14.4). Never closed by an unexplained entry."""

    __tablename__ = "reconciliation_cases"
    __table_args__ = (UniqueConstraint("dedupe_key"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    dedupe_key: Mapped[str] = mapped_column(Text)
    case_type: Mapped[str] = mapped_column(Text)
    refs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    difference_minor: Mapped[int | None]
    owner: Mapped[str] = mapped_column(Text, default="finance-ops")
    state: Mapped[str] = mapped_column(Text, default="open")
    resolution_evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    opened_at: Mapped[datetime] = created_at()
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

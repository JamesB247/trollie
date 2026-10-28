import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, created_at, uuid_pk


class DeliverySlot(Base):
    """A simulated courier window for one merchant location (blueprint §12.2).

    Each leg is delivered separately; consolidated pickup is disabled (D-S03.1).
    """

    __tablename__ = "delivery_slots"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="window_order"),
        CheckConstraint("booked <= capacity", name="within_capacity"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchant_locations.id"), index=True)
    courier_code: Mapped[str] = mapped_column(Text)
    zone: Mapped[str] = mapped_column(Text)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fee_minor: Mapped[int]
    capacity: Mapped[int]
    booked: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = created_at()

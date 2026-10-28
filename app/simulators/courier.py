"""Simulated courier ("swiftparcel-fictional"). Fault modes on `book`: timeout_after_effect,
timeout_before_effect, reject."""

import uuid

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.clock import Clock
from app.simulators.faults import take
from app.simulators.models import SimCourierBooking


class CourierTimeout(Exception):
    """No response; look the booking up by reference before any rebooking (T40)."""


class SimulatedCourier:
    def __init__(self, engine: Engine, clock: Clock) -> None:
        self.engine = engine
        self.clock = clock

    def book(
        self,
        *,
        booking_ref: str,
        slot_id: uuid.UUID,
        location_id: uuid.UUID,
        address_version_id: uuid.UUID,
    ) -> dict:
        with Session(self.engine) as s, s.begin():
            existing = s.get(SimCourierBooking, booking_ref)
            if existing is not None:
                return self._obs(existing)
            fault = take(s, system="courier", target="book", operation="book")
            if fault == "timeout_before_effect":
                raise CourierTimeout(booking_ref)
            if fault == "reject":
                return {"booking_ref": booking_ref, "status": "rejected"}
            booking = SimCourierBooking(
                booking_ref=booking_ref,
                courier_ref=f"SIMCOUR-{uuid.uuid4().hex[:10]}",
                slot_id=slot_id,
                location_id=location_id,
                address_version_id=address_version_id,
                state="booked",
            )
            s.add(booking)
            s.flush()
            obs = self._obs(booking)
        if fault == "timeout_after_effect":
            raise CourierTimeout(booking_ref)
        return obs

    def get_booking(self, *, booking_ref: str) -> dict:
        with Session(self.engine) as s:
            booking = s.get(SimCourierBooking, booking_ref)
            return (
                self._obs(booking)
                if booking
                else {"booking_ref": booking_ref, "status": "not_found"}
            )

    def advance(self, *, booking_ref: str, to: str) -> dict:
        """Driver-side progression: collected | delivered | failed."""
        with Session(self.engine) as s, s.begin():
            booking = s.get(SimCourierBooking, booking_ref, with_for_update=True)
            booking.state = to
            return self._obs(booking)

    @staticmethod
    def _obs(b: SimCourierBooking) -> dict:
        return {
            "booking_ref": b.booking_ref,
            "courier_ref": b.courier_ref,
            "status": b.state,
            "address_version_id": str(b.address_version_id),
        }

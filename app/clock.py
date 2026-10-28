"""Injectable clock. Instants are UTC; Africa/Johannesburg is for presentation only."""

from datetime import UTC, datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

PRESENTATION_TZ = ZoneInfo("Africa/Johannesburg")


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """Deterministic clock for tests and fixtures; only moves when told to."""

    def __init__(self, start: datetime) -> None:
        if start.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware start")
        self._now = start.astimezone(UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs: float) -> datetime:
        self._now += timedelta(**kwargs)
        return self._now

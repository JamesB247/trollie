"""Transactional outbox (blueprint §6.3).

`emit` runs in the same database transaction as the business state change.
`dispatch` turns committed events into one job per subscriber; it can be re-run
after a crash without losing or duplicating subscriber work (T50).
"""

import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import Clock
from app.durable import jobs
from app.durable.models import OutboxEvent


def emit(
    session: Session,
    *,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    aggregate_version: int,
    event_type: str,
    payload: dict[str, Any],
) -> uuid.UUID:
    event = OutboxEvent(
        id=uuid.uuid4(),
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        aggregate_version=aggregate_version,
        event_type=event_type,
        payload=payload,
    )
    session.add(event)
    return event.id


def dispatch(
    session: Session,
    subscribers: Mapping[str, list[str]],
    *,
    clock: Clock,
    batch: int = 100,
) -> int:
    """Publish up to `batch` committed events. Returns the number published."""
    with session.begin():
        events = session.scalars(
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.created_at, OutboxEvent.id)
            .limit(batch)
            .with_for_update(skip_locked=True)
        ).all()
        now = clock.now()
        for event in events:
            for kind in subscribers.get(event.event_type, []):
                jobs.enqueue(
                    session,
                    kind,
                    {
                        "event_id": str(event.id),
                        "event_type": event.event_type,
                        "aggregate_type": event.aggregate_type,
                        "aggregate_id": str(event.aggregate_id),
                        "aggregate_version": event.aggregate_version,
                        "payload": event.payload,
                    },
                    now=now,
                    dedupe_key=f"outbox:{event.id}:{kind}",
                )
            event.published_at = now
        return len(events)

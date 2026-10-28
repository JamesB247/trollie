"""Postgres-backed job queue (DECISIONS.md D-S03.4).

At-least-once: a job may run more than once (crash after effect, before ack).
Handlers must be idempotent; financial idempotency, not the queue, prevents
duplicate economic effects.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.clock import Clock
from app.durable.models import Job, JobState

BASE_BACKOFF = timedelta(seconds=2)
MAX_BACKOFF = timedelta(minutes=10)


@dataclass(frozen=True)
class Lease:
    job_id: uuid.UUID
    token: uuid.UUID
    kind: str
    payload: dict[str, Any]
    attempt: int


def enqueue(
    session: Session,
    kind: str,
    payload: dict[str, Any],
    *,
    now: datetime,
    dedupe_key: str | None = None,
    delay: timedelta = timedelta(0),
    max_attempts: int = 8,
) -> None:
    """Enqueue inside the caller's transaction. A repeated dedupe_key is a no-op."""
    stmt = insert(Job).values(
        id=uuid.uuid4(),
        kind=kind,
        payload=payload,
        dedupe_key=dedupe_key,
        state=JobState.READY,
        available_at=now + delay,
        max_attempts=max_attempts,
    )
    session.execute(stmt.on_conflict_do_nothing(index_elements=["dedupe_key"]))


def claim(
    session: Session,
    *,
    worker: str,
    clock: Clock,
    kinds: list[str] | None = None,
    lease: timedelta = timedelta(seconds=60),
) -> Lease | None:
    """Claim one job in a short transaction and commit the lease immediately.

    Leased jobs whose lease expired (worker crashed) are claimable again.
    """
    now = clock.now()
    query = (
        select(Job)
        .where(
            or_(
                (Job.state == JobState.READY) & (Job.available_at <= now),
                (Job.state == JobState.LEASED) & (Job.lease_expires_at < now),
            )
        )
        .order_by(Job.available_at, Job.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if kinds is not None:
        query = query.where(Job.kind.in_(kinds))
    with session.begin():
        job = session.scalars(query).one_or_none()
        if job is None:
            return None
        if job.attempts >= job.max_attempts:
            job.state = JobState.DEAD
            job.last_error = job.last_error or "lease expired after final attempt"
            return None
        job.state = JobState.LEASED
        job.attempts += 1
        job.lease_owner = worker
        job.lease_token = uuid.uuid4()
        job.lease_expires_at = now + lease
        return Lease(job.id, job.lease_token, job.kind, dict(job.payload), job.attempts)


def ack(session: Session, lease: Lease) -> bool:
    """Mark done. Returns False when the lease was lost (another worker took over)."""
    result = session.execute(
        update(Job)
        .where(Job.id == lease.job_id, Job.lease_token == lease.token)
        .values(state=JobState.DONE, lease_token=None, lease_expires_at=None)
    )
    return result.rowcount == 1


def fail(session: Session, lease: Lease, error: str, *, clock: Clock) -> None:
    job = session.get(Job, lease.job_id, with_for_update=True)
    if job is None or job.lease_token != lease.token:
        return
    backoff = min(BASE_BACKOFF * (2 ** (job.attempts - 1)), MAX_BACKOFF)
    job.last_error = error[:2000]
    job.lease_token = None
    job.lease_expires_at = None
    if job.attempts >= job.max_attempts:
        job.state = JobState.DEAD
    else:
        job.state = JobState.READY
        job.available_at = clock.now() + backoff

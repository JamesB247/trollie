"""Single-step worker loop: claim one job, run its handler, ack in the same transaction."""

import logging
from collections.abc import Callable, Mapping
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.clock import Clock
from app.durable import jobs

log = logging.getLogger(__name__)

Handler = Callable[[Session, dict[str, Any]], None]


def run_once(
    sessions: sessionmaker[Session],
    handlers: Mapping[str, Handler],
    *,
    worker: str,
    clock: Clock,
) -> bool:
    """Process one job. Returns False when nothing was claimable.

    Local effects and the ack commit together. A crash before commit leaves the
    lease to expire and the job runs again, so handlers must be idempotent.
    """
    with sessions() as session:
        lease = jobs.claim(session, worker=worker, clock=clock, kinds=list(handlers))
    if lease is None:
        return False
    with sessions() as session:
        try:
            with session.begin():
                handlers[lease.kind](session, lease.payload)
                if not jobs.ack(session, lease):
                    raise RuntimeError("lease lost before ack")
        except Exception as exc:  # noqa: BLE001 - every failure is recorded on the job
            log.warning("job %s (%s) failed: %s", lease.job_id, lease.kind, exc)
            with session.begin():
                jobs.fail(session, lease, f"{type(exc).__name__}: {exc}", clock=clock)
    return True


def drain(
    sessions: sessionmaker[Session],
    handlers: Mapping[str, Handler],
    *,
    worker: str,
    clock: Clock,
    limit: int = 1000,
) -> int:
    count = 0
    while count < limit and run_once(sessions, handlers, worker=worker, clock=clock):
        count += 1
    return count

"""Verified event inbox (blueprint §10.3; T28, T29).

The signature is verified over the exact raw body before anything is parsed.
Valid events are stored once per (provider, account, environment, event_id) and
processed asynchronously. Invalid or conflicting events change no state.
"""

import hmac
import json
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.clock import Clock
from app.durable import jobs
from app.durable.hashing import canonical_hash, sha256_hex
from app.durable.models import InboxEvent, RejectedEvent

SIGNATURE_TOLERANCE = timedelta(minutes=5)
PROCESS_JOB = "inbox.process"


class IngestStatus(StrEnum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"


@dataclass(frozen=True)
class IngestResult:
    status: IngestStatus
    reason: str | None = None
    inbox_id: str | None = None


def sign(secret: bytes, timestamp: int, body: bytes) -> str:
    """HMAC-SHA256 over '<timestamp>.<raw body>'. Used by the simulated providers."""
    return hmac.new(secret, f"{timestamp}.".encode() + body, "sha256").hexdigest()


def _reject(session: Session, provider: str, body: bytes, reason: str, event_id: str | None):
    session.add(
        RejectedEvent(
            provider=provider, reason=reason, event_id=event_id, body_hash=sha256_hex(body)
        )
    )
    return IngestResult(IngestStatus.REJECTED, reason)


def ingest(
    session: Session,
    *,
    provider: str,
    expected_account: str,
    expected_environment: str,
    secret: bytes,
    body: bytes,
    signature: str | None,
    timestamp: str | None,
    clock: Clock,
) -> IngestResult:
    """Verify and store one provider event inside the caller's transaction."""
    if not signature or not timestamp or not timestamp.isdigit():
        return _reject(session, provider, body, "missing_signature", None)
    expected = sign(secret, int(timestamp), body)
    if not hmac.compare_digest(expected, signature):
        return _reject(session, provider, body, "invalid_signature", None)
    age = abs(clock.now().timestamp() - int(timestamp))
    if age > SIGNATURE_TOLERANCE.total_seconds():
        return _reject(session, provider, body, "stale_signature", None)

    try:
        event = json.loads(body)
        event_id, event_type = str(event["id"]), str(event["type"])
        account, environment = str(event["account"]), str(event["environment"])
        data = event["data"]
    except (ValueError, KeyError, TypeError):
        return _reject(session, provider, body, "malformed_event", None)
    if account != expected_account or environment != expected_environment:
        return _reject(session, provider, body, "wrong_account_or_environment", event_id)

    payload_hash = canonical_hash(data)
    inserted = session.execute(
        insert(InboxEvent)
        .values(
            provider=provider,
            provider_account=account,
            environment=environment,
            event_id=event_id,
            event_type=event_type,
            payload_hash=payload_hash,
            payload=data,
        )
        .on_conflict_do_nothing(
            index_elements=["provider", "provider_account", "environment", "event_id"]
        )
        .returning(InboxEvent.id)
    ).scalar_one_or_none()
    if inserted is None:
        known = session.scalars(
            select(InboxEvent).where(
                InboxEvent.provider == provider,
                InboxEvent.provider_account == account,
                InboxEvent.environment == environment,
                InboxEvent.event_id == event_id,
            )
        ).one()
        if known.payload_hash != payload_hash:
            return _reject(session, provider, body, "payload_conflict", event_id)
        return IngestResult(IngestStatus.DUPLICATE, inbox_id=str(known.id))

    jobs.enqueue(
        session,
        PROCESS_JOB,
        {"inbox_id": str(inserted)},
        now=clock.now(),
        dedupe_key=f"inbox:{inserted}",
    )
    return IngestResult(IngestStatus.ACCEPTED, inbox_id=str(inserted))

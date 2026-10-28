"""Durable operations: T25 (idempotency), T28/T29 (inbox), T50 (outbox restore), job queue."""

import json
import threading
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.clock import FixedClock
from app.durable import idempotency, inbox, jobs, outbox, worker
from app.durable.models import InboxEvent, Job, JobState, OutboxEvent, RejectedEvent
from app.errors import ErrorCode, TrollieError

T0 = datetime(2026, 11, 2, 8, 0, tzinfo=UTC)


# --- T25: business-operation idempotency ---------------------------------------------


def test_t25_same_key_same_request_replays(db: Session):
    key = str(uuid.uuid4())
    op = idempotency.begin(db, scope="orders.create", key=key, request={"quote": "q1", "v": 1})
    assert not op.replay
    op.complete({"order_id": "o1"})
    db.commit()
    again = idempotency.begin(db, scope="orders.create", key=key, request={"v": 1, "quote": "q1"})
    assert again.replay and again.response == {"order_id": "o1"}
    db.commit()


def test_t25_same_key_changed_payload_conflicts(db: Session):
    key = str(uuid.uuid4())
    idempotency.begin(db, scope="orders.create", key=key, request={"quote": "q1"}).complete({})
    db.commit()
    with pytest.raises(TrollieError) as err:
        idempotency.begin(db, scope="orders.create", key=key, request={"quote": "q2"})
    assert err.value.code is ErrorCode.DUPLICATE_OPERATION_CONFLICT
    db.rollback()


def test_t25_concurrent_same_key_has_one_effect(sessions: sessionmaker[Session]):
    key = str(uuid.uuid4())
    effects: list[str] = []
    barrier = threading.Barrier(2)

    def attempt(name: str) -> None:
        with sessions() as s:
            barrier.wait()
            op = idempotency.begin(s, scope="charge", key=key, request={"amount": 110000})
            if not op.replay:
                effects.append(name)
                op.complete({"by": name})
            s.commit()

    threads = [threading.Thread(target=attempt, args=(n,)) for n in ("a", "b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(effects) == 1


def test_canonical_payload_rejects_floats(db: Session):
    with pytest.raises(ValueError):
        idempotency.begin(db, scope="x", key=str(uuid.uuid4()), request={"amount": 1.5})


# --- Job queue ----------------------------------------------------------------------


def _kind() -> str:
    return f"test.{uuid.uuid4()}"


def test_enqueue_dedupes(db: Session, clock: FixedClock):
    kind, dedupe = _kind(), str(uuid.uuid4())
    jobs.enqueue(db, kind, {"n": 1}, now=clock.now(), dedupe_key=dedupe)
    jobs.enqueue(db, kind, {"n": 2}, now=clock.now(), dedupe_key=dedupe)
    db.commit()
    assert db.scalar(select(func.count()).select_from(Job).where(Job.kind == kind)) == 1


def test_claim_ack_and_backoff(db: Session, clock: FixedClock):
    kind = _kind()
    jobs.enqueue(db, kind, {}, now=clock.now(), max_attempts=2)
    db.commit()
    lease = jobs.claim(db, worker="w1", clock=clock, kinds=[kind])
    assert lease is not None and lease.attempt == 1
    with db.begin():
        jobs.fail(db, lease, "boom", clock=clock)
    assert jobs.claim(db, worker="w1", clock=clock, kinds=[kind]) is None  # backing off
    clock.advance(seconds=3)
    lease = jobs.claim(db, worker="w1", clock=clock, kinds=[kind])
    assert lease is not None and lease.attempt == 2
    with db.begin():
        jobs.fail(db, lease, "boom again", clock=clock)
    job = db.get(Job, lease.job_id, populate_existing=True)
    assert job.state == JobState.DEAD and job.last_error == "boom again"


def test_expired_lease_is_reclaimed_after_worker_crash(db: Session, clock: FixedClock):
    kind = _kind()
    jobs.enqueue(db, kind, {}, now=clock.now())
    db.commit()
    crashed = jobs.claim(db, worker="crashed", clock=clock, kinds=[kind])
    assert jobs.claim(db, worker="w2", clock=clock, kinds=[kind]) is None
    clock.advance(seconds=61)
    taken_over = jobs.claim(db, worker="w2", clock=clock, kinds=[kind])
    assert taken_over is not None and taken_over.job_id == crashed.job_id
    with db.begin():
        assert jobs.ack(db, crashed) is False  # the crashed worker's late ack is ignored
        assert jobs.ack(db, taken_over) is True


def test_concurrent_workers_never_claim_the_same_job(
    sessions: sessionmaker[Session], clock: FixedClock
):
    kind = _kind()
    with sessions() as s, s.begin():
        for i in range(20):
            jobs.enqueue(s, kind, {"i": i}, now=clock.now())
    claimed: list[uuid.UUID] = []
    lock = threading.Lock()

    def work() -> None:
        with sessions() as s:
            while (lease := jobs.claim(s, worker="w", clock=clock, kinds=[kind])) is not None:
                with lock:
                    claimed.append(lease.job_id)

    threads = [threading.Thread(target=work) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(claimed) == 20 and len(set(claimed)) == 20


# --- Outbox (T50) --------------------------------------------------------------------


def test_outbox_event_only_exists_if_business_transaction_commits(db: Session):
    agg = uuid.uuid4()
    outbox.emit(
        db,
        aggregate_type="order",
        aggregate_id=agg,
        aggregate_version=1,
        event_type="order.created",
        payload={},
    )
    db.rollback()
    assert db.scalar(select(func.count()).where(OutboxEvent.aggregate_id == agg)) == 0


def test_t50_restore_after_outbox_commit_before_dispatch(
    db: Session, sessions: sessionmaker[Session], clock: FixedClock
):
    """Events committed before a crash are dispatched after restart, exactly once per subscriber,
    and a handler that runs twice produces one effect."""
    event_type = f"test.{uuid.uuid4()}"
    kind = f"handler.{uuid.uuid4()}"
    agg = uuid.uuid4()
    with db.begin():
        outbox.emit(
            db,
            aggregate_type="order",
            aggregate_id=agg,
            aggregate_version=1,
            event_type=event_type,
            payload={"amount_minor": 110000},
        )
    # "Crash": nothing dispatched yet. On restart the dispatcher finds the committed event.
    subscribers = {event_type: [kind]}
    while outbox.dispatch(db, subscribers, clock=clock):
        pass
    outbox.dispatch(db, subscribers, clock=clock)  # re-running after restart is harmless
    assert db.scalar(select(func.count()).select_from(Job).where(Job.kind == kind)) == 1

    effects: set[str] = set()

    def handler(session: Session, payload: dict) -> None:
        # Idempotent effect keyed by the source event id.
        effects.add(payload["event_id"])

    # First run "crashes" after the effect but before ack: simulate by claiming and abandoning.
    with sessions() as s:
        abandoned = jobs.claim(s, worker="crashed", clock=clock, kinds=[kind])
    handler(None, abandoned.payload)  # type: ignore[arg-type]
    clock.advance(seconds=61)
    assert worker.run_once(sessions, {kind: handler}, worker="w2", clock=clock)
    assert len(effects) == 1
    assert db.get(Job, abandoned.job_id, populate_existing=True).state == JobState.DONE


# --- Inbox (T28, T29) ----------------------------------------------------------------

SECRET = b"test-webhook-secret"


def _event(event_id: str | None = None, **data) -> dict:
    return {
        "id": event_id or str(uuid.uuid4()),
        "type": "payment.succeeded",
        "account": "sim-acct-1",
        "environment": "test",
        "data": data or {"operation_ref": "op-1", "amount_minor": 110000},
    }


def _ingest(
    db: Session,
    clock: FixedClock,
    body: bytes,
    signature: str | None = None,
    timestamp: int | None = None,
):
    ts = int(clock.now().timestamp()) if timestamp is None else timestamp
    sig = inbox.sign(SECRET, ts, body) if signature is None else signature
    return inbox.ingest(
        db,
        provider="simpay",
        expected_account="sim-acct-1",
        expected_environment="test",
        secret=SECRET,
        body=body,
        signature=sig,
        timestamp=str(ts),
        clock=clock,
    )


def _inbox_count(db: Session, event_id: str) -> int:
    return db.scalar(select(func.count()).where(InboxEvent.event_id == event_id))


def test_valid_event_is_stored_and_queued(db: Session, clock: FixedClock):
    event = _event()
    result = _ingest(db, clock, json.dumps(event).encode())
    db.commit()
    assert result.status is inbox.IngestStatus.ACCEPTED
    assert _inbox_count(db, event["id"]) == 1
    assert db.scalar(select(func.count()).where(Job.dedupe_key == f"inbox:{result.inbox_id}")) == 1


def test_t28_duplicate_webhook_is_idempotent(db: Session, clock: FixedClock):
    event = _event()
    first = _ingest(db, clock, json.dumps(event).encode())
    # Same event, different JSON key order and a later delivery.
    clock.advance(seconds=30)
    second = _ingest(db, clock, json.dumps(dict(reversed(event.items()))).encode())
    db.commit()
    assert second.status is inbox.IngestStatus.DUPLICATE and second.inbox_id == first.inbox_id
    assert _inbox_count(db, event["id"]) == 1


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda b, ts, sig: (b, ts, "0" * 64), "invalid_signature"),
        (lambda b, ts, sig: (b.replace(b"110000", b"990000"), ts, sig), "invalid_signature"),
        (lambda b, ts, sig: (b, ts, ""), "missing_signature"),
        (lambda b, ts, sig: (b, ts - 3600, inbox.sign(SECRET, ts - 3600, b)), "stale_signature"),
    ],
)
def test_t29_invalid_signature_rejected_without_state_change(
    db: Session, clock: FixedClock, mutate, reason
):
    event = _event()
    body = json.dumps(event).encode()
    ts = int(clock.now().timestamp())
    body, ts, sig = mutate(body, ts, inbox.sign(SECRET, ts, body))
    result = _ingest(db, clock, body, signature=sig, timestamp=ts)
    db.commit()
    assert result.status is inbox.IngestStatus.REJECTED and result.reason == reason
    assert _inbox_count(db, event["id"]) == 0


def test_conflicting_payload_for_known_event_is_rejected(db: Session, clock: FixedClock):
    event = _event()
    _ingest(db, clock, json.dumps(event).encode())
    tampered = {**event, "data": {"operation_ref": "op-1", "amount_minor": 1}}
    result = _ingest(db, clock, json.dumps(tampered).encode())
    db.commit()
    assert result.reason == "payload_conflict"
    stored = db.scalars(select(InboxEvent).where(InboxEvent.event_id == event["id"])).one()
    assert stored.payload["amount_minor"] == 110000
    assert db.scalar(select(func.count()).where(RejectedEvent.event_id == event["id"])) == 1


def test_event_for_another_account_is_rejected(db: Session, clock: FixedClock):
    event = {**_event(), "account": "someone-else"}
    result = _ingest(db, clock, json.dumps(event).encode())
    db.commit()
    assert result.reason == "wrong_account_or_environment"
    assert _inbox_count(db, event["id"]) == 0

"""Job handlers wiring verified provider events and outbox events to orchestration."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.durable import inbox, jobs, outbox, worker
from app.durable.models import InboxEvent, InboxState
from app.orders.runtime import Runtime
from app.orders.service import advance
from app.payments.adapter import PaymentObservation
from app.payments.models import FinancialOperation, Refund
from app.payments.operations import apply_observation
from app.payments.refunds import sync_refund
from app.reconciliation.service import open_case

ADVANCE = "order.advance"
SUBSCRIBERS: dict[str, list[str]] = {}


def ingest_webhook(rt: Runtime, body: bytes, signature: str | None, timestamp: str | None):
    """Webhook endpoint body: verify, store once, queue processing."""
    with rt.sessions() as s, s.begin():
        return inbox.ingest(
            s,
            provider="simpay",
            expected_account=rt.provider_account,
            expected_environment=rt.environment,
            secret=rt.webhook_secret,
            body=body,
            signature=signature,
            timestamp=timestamp,
            clock=rt.clock,
        )


def _process_inbox(rt: Runtime):
    def handle(session: Session, payload: dict[str, Any]) -> None:
        event = session.get(InboxEvent, uuid.UUID(payload["inbox_id"]), with_for_update=True)
        if event.state != InboxState.RECEIVED:
            return
        data = event.payload
        op = session.scalars(
            select(FinancialOperation)
            .where(FinancialOperation.idempotency_key == data.get("client_key"))
            .with_for_update()
        ).one_or_none()
        if op is None:
            open_case(
                session,
                dedupe_key=f"unmatched:{event.id}",
                case_type="unmatched_provider_event",
                refs={"inbox_id": str(event.id), "event_type": event.event_type},
            )
        else:
            obs = PaymentObservation(
                status=data["status"],
                provider_ref=data["provider_ref"],
                amount_minor=data.get("amount_minor"),
            )
            apply_observation(session, op, obs, source="webhook", now=rt.clock.now())
            refund = session.scalars(select(Refund).where(Refund.operation_id == op.id)).first()
            if refund is not None and refund.provider_allocation is None and data.get("allocation"):
                refund.provider_allocation = data["allocation"]
            if op.order_id is not None:
                jobs.enqueue(
                    session,
                    ADVANCE,
                    {"order_id": str(op.order_id), "refund_id": str(refund.id) if refund else None},
                    now=rt.clock.now(),
                    dedupe_key=f"advance:{event.id}",
                )
        event.state = InboxState.PROCESSED

    return handle


def _advance(rt: Runtime):
    def handle(session: None, payload: dict[str, Any]) -> None:
        if payload.get("refund_id"):
            sync_refund(rt, uuid.UUID(payload["refund_id"]))
        advance(rt, uuid.UUID(payload["order_id"]))

    handle.own_transactions = True  # type: ignore[attr-defined]
    return handle


def handlers(rt: Runtime) -> dict[str, worker.Handler]:
    return {inbox.PROCESS_JOB: _process_inbox(rt), ADVANCE: _advance(rt)}


def pump(rt: Runtime, provider, *, rounds: int = 20) -> None:
    """Deliver provider webhooks, dispatch the outbox and run jobs until quiet."""
    hs = handlers(rt)
    for _ in range(rounds):
        sent = provider.deliver_webhooks(lambda b, sig, ts: ingest_webhook(rt, b, sig, ts))
        with rt.sessions() as s:
            published = outbox.dispatch(s, SUBSCRIBERS, clock=rt.clock)
        ran = worker.drain(rt.sessions, hs, worker="pump", clock=rt.clock)
        if not (sent or published or ran):
            if not sweep(rt):
                return


def sweep(rt: Runtime) -> int:
    """Periodic reconciler: re-drive orders that are waiting on unresolved external state,
    e.g. a lookup that timed out. Returns the number of orders whose state changed."""
    from app.orders.models import Order

    with rt.sessions() as s:
        pending = [
            (o.id, o.version)
            for o in s.scalars(
                select(Order).where(
                    Order.state.in_(["PAYMENT_PENDING", "COMMITTING", "COMPENSATING", "FULFILLING"])
                )
            )
        ]
    changed = 0
    for order_id, version in pending:
        advance(rt, order_id)
        with rt.sessions() as s:
            if s.get(Order, order_id).version != version:
                changed += 1
    with rt.sessions() as s:
        open_refunds = [
            (r.id, r.operation_id, r.state)
            for r in s.scalars(
                select(Refund).where(Refund.state.in_(["SUBMITTED", "PENDING", "UNKNOWN"]))
            )
        ]
    for refund_id, op_id, state in open_refunds:
        rt.executor.reconcile(op_id)
        if sync_refund(rt, refund_id) != state:
            changed += 1
    return changed

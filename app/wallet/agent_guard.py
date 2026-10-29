"""Guard against a stolen or misbehaving agent (I-046).

An agent token that keeps trying things its grant does not allow is treated as
compromised: after a few refused attempts in a short window the agent is suspended, its
grants stop working, and the owner is told. An agent may also only push a limited number
of purchase requests per window, so a thief cannot bury the owner in approval prompts.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.controls.models import AuditEvent, Incident
from app.durable import outbox
from app.errors import ErrorCode, TrollieError
from app.wallet.models import Agent, Grant


def _window(now: datetime):
    """Window start in database time: audit rows are stamped by the database clock."""
    del now
    return func.now() - timedelta(minutes=get_settings().agent_strike_window_minutes)


def ensure_active(s: Session, agent_id: uuid.UUID) -> None:
    agent = s.get(Agent, agent_id)
    if agent is None or agent.suspended_at is not None:
        raise TrollieError(
            ErrorCode.AUTHORITY_DENIED,
            "this agent is suspended; its owner must review it",
            reason=(agent.suspended_reason if agent else "unknown agent"),
        )


def record_strike(s: Session, agent_id: uuid.UUID, what: str, now: datetime) -> bool:
    """Record one refused attempt. Returns True if the agent is now suspended."""
    agent = s.get(Agent, agent_id, with_for_update=True)
    if agent is None or agent.suspended_at is not None:
        return False
    actor = f"agent:{agent_id}"
    s.add(
        AuditEvent(
            actor=actor, action="agent.denied", object_type="agent", object_id=str(agent_id),
            result="refused", details={"what": what[:200]},
        )
    )  # fmt: skip
    s.flush()
    strikes = s.scalar(
        select(func.count())
        .select_from(AuditEvent)
        .where(
            AuditEvent.actor == actor,
            AuditEvent.action == "agent.denied",
            AuditEvent.created_at >= _window(now),
        )
    )
    if strikes < get_settings().agent_strike_limit:
        return False
    suspend(s, agent, f"{strikes} refused attempts within the hour, latest: {what}"[:300], now)
    return True


def suspend(s: Session, agent: Agent, reason: str, now: datetime) -> None:
    agent.suspended_at = now
    agent.suspended_reason = reason
    for grant in s.scalars(
        select(Grant).where(
            Grant.agent_id == agent.id, Grant.status.in_(["active", "pending_approval"])
        )
    ):
        grant.status = "suspended"
    s.add(
        Incident(
            kind="agent_suspended",
            severity="high",
            details={
                "agent_id": str(agent.id),
                "account_id": str(agent.account_id),
                "reason": reason,
            },
        )
    )
    outbox.emit(
        s,
        aggregate_type="agent",
        aggregate_id=agent.id,
        aggregate_version=1,
        event_type="agent.suspended",
        payload={"account_id": str(agent.account_id), "reason": reason},
    )


def check_request_rate(s: Session, agent_id: uuid.UUID, now: datetime) -> None:
    cfg = get_settings()
    sent = s.scalar(
        select(func.count())
        .select_from(AuditEvent)
        .where(
            AuditEvent.actor == f"agent:{agent_id}",
            AuditEvent.action == "purchase.request",
            AuditEvent.created_at >= _window(now),
        )
    )
    if sent >= cfg.agent_requests_per_window:
        raise TrollieError(
            ErrorCode.RATE_LIMITED,
            "this agent has sent too many purchase requests; ask the owner to review them",
        )

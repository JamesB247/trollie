"""Kill switch, incident and audit helpers."""

from typing import Any

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.controls.models import AuditEvent, Incident, KillSwitch
from app.errors import ErrorCode, TrollieError
from app.redaction import redact

FINANCIAL = "financial"


def audit(
    session: Session,
    *,
    actor: str,
    action: str,
    object_type: str,
    object_id: object = None,
    result: str = "ok",
    correlation_id: str | None = None,
    **details: Any,
) -> None:
    session.add(
        AuditEvent(
            actor=actor,
            action=action,
            object_type=object_type,
            object_id=None if object_id is None else str(object_id),
            result=result,
            correlation_id=correlation_id,
            details=redact(details),
        )
    )


def engaged_scopes(session: Session, scopes: list[str]) -> list[str]:
    rows = session.scalars(
        select(KillSwitch.scope).where(KillSwitch.scope.in_(scopes), KillSwitch.engaged)
    )
    return list(rows)


def require_not_paused(session: Session, *scopes: str) -> None:
    """Called before any new economic commitment. Refunds and reconciliation do not call it."""
    paused = engaged_scopes(session, [FINANCIAL, *scopes])
    if paused:
        raise TrollieError(
            ErrorCode.FINANCIAL_ACTIONS_PAUSED, "new financial actions are paused", scopes=paused
        )


def set_kill_switch(session: Session, scope: str, engaged: bool, *, reason: str, by: str) -> None:
    switch = session.get(KillSwitch, scope, with_for_update=True)
    if switch is None:
        switch = KillSwitch(scope=scope, changed_by=by)
        session.add(switch)
    switch.engaged = engaged
    switch.reason = reason
    switch.changed_by = by
    audit(
        session,
        actor=by,
        action="kill_switch.engage" if engaged else "kill_switch.release",
        object_type="kill_switch",
        object_id=scope,
        reason=reason,
    )


def raise_incident_and_pause(engine: Engine, *, kind: str, scope: str, **details: Any) -> None:
    """Record an incident and engage a kill switch in an independent transaction.

    Used when the caller's own transaction is about to roll back, so the alert
    survives the failure it reports.
    """
    with Session(engine) as session, session.begin():
        session.add(Incident(kind=kind, severity="critical", details=redact(details)))
        set_kill_switch(session, scope, True, reason=kind, by="system")

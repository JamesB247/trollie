"""Fault injection shared by the simulators."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.simulators.models import SimFault


def inject(
    session: Session, *, system: str, target: str, operation: str, mode: str, times: int = 1
) -> None:
    session.add(
        SimFault(system=system, target=target, operation=operation, mode=mode, remaining=times)
    )


def take(session: Session, *, system: str, target: str, operation: str) -> str | None:
    """Consume one pending fault for this call, if any, and return its mode."""
    fault = session.scalars(
        select(SimFault)
        .where(
            SimFault.system == system,
            SimFault.target == target,
            SimFault.operation == operation,
            SimFault.remaining > 0,
        )
        .order_by(SimFault.created_at, SimFault.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).one_or_none()
    if fault is None:
        return None
    fault.remaining -= 1
    return fault.mode

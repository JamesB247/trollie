"""Fault injection shared by the simulators.

Mode `pass` consumes a slot without misbehaving, so a test can fail the Nth call.
"""

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
    """Consume one pending fault for this call, if any, and return its mode.

    Consumption commits in its own transaction: a simulated timeout that rolls back the
    simulated action must still use up the fault, or it would fire forever.
    """
    with Session(session.get_bind()) as control, control.begin():
        fault = control.scalars(
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

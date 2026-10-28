"""Reconciliation cases: every break has an owner, an age, an amount and references."""

from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.controls.service import audit
from app.reconciliation.models import ReconciliationCase


def open_case(
    session: Session,
    *,
    dedupe_key: str,
    case_type: str,
    refs: dict[str, Any],
    difference_minor: int | None = None,
    owner: str = "finance-ops",
) -> None:
    """Open a case once per dedupe key. Opening a case never posts a balancing entry."""
    inserted = session.execute(
        insert(ReconciliationCase)
        .values(
            dedupe_key=dedupe_key,
            case_type=case_type,
            refs=refs,
            difference_minor=difference_minor,
            owner=owner,
        )
        .on_conflict_do_nothing(index_elements=["dedupe_key"])
        .returning(ReconciliationCase.id)
    ).scalar_one_or_none()
    if inserted is not None:
        audit(
            session,
            actor="system",
            action="reconciliation.open",
            object_type="case",
            object_id=inserted,
            case_type=case_type,
        )

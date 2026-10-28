"""Restricted financial executor (blueprint §6.2, §9.4, §10.3).

- Persist intent -> call provider outside any DB transaction -> persist observation.
- An idempotency key belongs to one logical operation forever; it is never regenerated.
- A timeout is UNKNOWN, resolved by lookup. A lookup that finds nothing inside the
  provider's idempotency horizon means the request never landed, so the same request is
  replayed with the same key. Beyond the horizon automatic replay is blocked (T27).
- Evidence that contradicts a final state opens a reconciliation case (T30).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.clock import Clock
from app.durable.hashing import canonical_hash
from app.errors import ErrorCode, TrollieError
from app.orders.state import OPERATION
from app.payments.adapter import (
    IdempotencyConflict,
    PaymentAdapter,
    PaymentObservation,
    PaymentTimeout,
)
from app.payments.models import Action, FinancialOperation, OpState
from app.payments.profiles import PROFILES, CapabilityProfile
from app.reconciliation.service import open_case

FINAL = (OpState.SUCCEEDED, OpState.FAILED_FINAL)

_STATUS = {
    Action.AUTHORISE: {
        "requires_customer_action": OpState.PENDING,
        "authorised": OpState.SUCCEEDED,
        "captured": OpState.SUCCEEDED,
        "voided": OpState.SUCCEEDED,
        "failed": OpState.FAILED_FINAL,
    },
    Action.CHARGE: {
        "requires_customer_action": OpState.PENDING,
        "succeeded": OpState.SUCCEEDED,
        "failed": OpState.FAILED_FINAL,
    },
}
_DEFAULT = {
    "succeeded": OpState.SUCCEEDED,
    "pending": OpState.PENDING,
    "failed": OpState.FAILED_FINAL,
}


def target_state(action: str, status: str) -> str | None:
    return _STATUS.get(Action(action), _DEFAULT).get(status)


def create_operation(
    session: Session,
    *,
    order_id: uuid.UUID | None,
    action: Action,
    profile: CapabilityProfile,
    amount_minor: int,
    idempotency_key: str,
    request: dict[str, Any],
    parent_id: uuid.UUID | None = None,
    subject_type: str = "order",
) -> FinancialOperation:
    """Create the operation once. A second call with the same key must be the same request."""
    request_hash = canonical_hash({"action": action, "amount": amount_minor, **request})
    existing = session.scalars(
        select(FinancialOperation).where(FinancialOperation.idempotency_key == idempotency_key)
    ).one_or_none()
    if existing is not None:
        if existing.request_hash != request_hash:
            raise TrollieError(
                ErrorCode.DUPLICATE_OPERATION_CONFLICT,
                "operation key reused with different content",
                key=idempotency_key,
            )
        return existing
    op = FinancialOperation(
        order_id=order_id,
        subject_type=subject_type,
        action=action,
        provider=profile.provider,
        profile_key=profile.key,
        profile_version=profile.version,
        amount_minor=amount_minor,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        parent_id=parent_id,
    )
    session.add(op)
    session.flush()
    return op


def apply_observation(
    session: Session, op: FinancialOperation, obs: PaymentObservation, *, source: str, now: datetime
) -> bool:
    """Record provider evidence. Returns True when the operation's state changed."""
    target = target_state(op.action, obs.status)
    op.last_observation = {
        "source": source,
        "status": obs.status,
        "provider_ref": obs.provider_ref,
        "amount_minor": obs.amount_minor,
        "reason": obs.reason,
        "observed_at": now.isoformat(),
    }
    if obs.provider_ref and op.external_ref is None:
        op.external_ref = obs.provider_ref
    if target is None:
        return False
    if op.state in FINAL and op.state != target:
        open_case(
            session,
            dedupe_key=f"conflict:{op.id}:{source}:{obs.status}",
            case_type="conflicting_provider_evidence",
            refs={
                "operation_id": str(op.id),
                "state": op.state,
                "observed": obs.status,
                "source": source,
            },
        )
        return False
    before = op.state
    if op.state == OpState.CREATED:
        OPERATION.move(op, OpState.SUBMITTED)
    OPERATION.move(op, target)
    return op.state != before


@dataclass
class Executor:
    sessions: sessionmaker[Session]
    provider: PaymentAdapter
    clock: Clock

    def _call(self, op: dict[str, Any]) -> PaymentObservation:
        action, key = op["action"], op["idempotency_key"]
        if action in (Action.AUTHORISE, Action.CHARGE):
            return self.provider.create_checkout(
                idempotency_key=key,
                collection=op["collection"],
                amount_minor=op["amount"],
                reference=op["reference"],
                beneficiaries=op["beneficiaries"],
            )
        if action == Action.CAPTURE:
            return self.provider.capture(
                idempotency_key=key,
                authorisation_ref=op["parent_ref"],
                amount_minor=op["amount"],
                beneficiaries=op.get("beneficiaries"),
            )
        if action == Action.VOID:
            return self.provider.void(idempotency_key=key, authorisation_ref=op["parent_ref"])
        if action == Action.REFUND:
            return self.provider.refund(
                idempotency_key=key, payment_ref=op["parent_ref"], amount_minor=op["amount"]
            )
        raise ValueError(action)

    def _call_args(self, s: Session, op: FinancialOperation, extra: dict[str, Any]) -> dict:
        parent = s.get(FinancialOperation, op.parent_id) if op.parent_id else None
        if parent is not None and parent.external_ref is None:
            raise TrollieError(ErrorCode.PROVIDER_STATE_UNKNOWN, "parent operation unresolved")
        return {
            "action": op.action,
            "idempotency_key": op.idempotency_key,
            "amount": op.amount_minor,
            "parent_ref": parent.external_ref if parent else None,
            **extra,
        }

    def submit(self, op_id: uuid.UUID, **extra: Any) -> FinancialOperation:
        """Send a CREATED operation exactly once. Any other state is left to reconciliation."""
        with self.sessions() as s, s.begin():
            op = s.get(FinancialOperation, op_id, with_for_update=True)
            if op.state != OpState.CREATED:
                return op
            args = self._call_args(s, op, extra)
            OPERATION.move(op, OpState.SUBMITTED)
            op.submitted_at = self.clock.now()
            op.request_args = extra
        return self._send_and_record(op_id, args)

    def _send_and_record(self, op_id: uuid.UUID, args: dict[str, Any]) -> FinancialOperation:
        try:
            obs = self._call(args)
        except PaymentTimeout:
            obs = None
        except IdempotencyConflict:
            with self.sessions() as s, s.begin():
                op = s.get(FinancialOperation, op_id, with_for_update=True)
                OPERATION.move(op, OpState.UNKNOWN)
                open_case(
                    s,
                    dedupe_key=f"idem-conflict:{op_id}",
                    case_type="idempotency_conflict",
                    refs={"operation_id": str(op_id)},
                )
                return op
        with self.sessions() as s, s.begin():
            op = s.get(FinancialOperation, op_id, with_for_update=True)
            if obs is None:
                if op.state not in FINAL:
                    OPERATION.move(op, OpState.UNKNOWN)
            else:
                apply_observation(s, op, obs, source="response", now=self.clock.now())
            return op

    def reconcile(self, op_id: uuid.UUID) -> FinancialOperation:
        """Resolve UNKNOWN/SUBMITTED/PENDING by lookup with the same key (T26, T27, T51)."""
        with self.sessions() as s, s.begin():
            op = s.get(FinancialOperation, op_id, with_for_update=True)
            if op.state in FINAL or op.state == OpState.CREATED:
                return op
            profile = PROFILES[op.profile_key]
            if (
                op.submitted_at
                and op.submitted_at + profile.idempotency_retention < self.clock.now()
            ):
                if op.state == OpState.UNKNOWN:
                    OPERATION.move(op, OpState.RECONCILING)
                open_case(
                    s,
                    dedupe_key=f"horizon:{op.id}",
                    case_type="unknown_beyond_horizon",
                    refs={"operation_id": str(op.id), "action": op.action},
                    difference_minor=op.amount_minor,
                )
                return op  # T27: no automatic resend; a person resolves it with evidence
            if op.state == OpState.UNKNOWN:
                OPERATION.move(op, OpState.RECONCILING)
            key = op.idempotency_key
            args = self._call_args(s, op, op.request_args)
        try:
            obs = self.provider.query(idempotency_key=key)
        except PaymentTimeout:
            with self.sessions() as s, s.begin():
                op = s.get(FinancialOperation, op_id, with_for_update=True)
                if op.state == OpState.RECONCILING:
                    OPERATION.move(op, OpState.UNKNOWN)
                return op
        if obs.status == "not_found":
            # Inside the horizon and unknown to the provider: it never received the request.
            return self._send_and_record(op_id, args)
        with self.sessions() as s, s.begin():
            op = s.get(FinancialOperation, op_id, with_for_update=True)
            apply_observation(s, op, obs, source="lookup", now=self.clock.now())
            return op

    def confirm(self, op_id: uuid.UUID) -> PaymentObservation | None:
        """Authoritative status query used before acting on a callback (T30)."""
        with self.sessions() as s:
            key = s.get(FinancialOperation, op_id).idempotency_key
        try:
            return self.provider.query(idempotency_key=key)
        except PaymentTimeout:
            return None

"""State machines (blueprint §8). Every transition checks the allowed predecessor and bumps
the row version; callers hold a row lock, so stale actors cannot overwrite current state."""

from dataclasses import dataclass
from typing import Any

from app.errors import ErrorCode, TrollieError


@dataclass(frozen=True)
class Machine:
    name: str
    transitions: dict[str, frozenset[str]]

    def can(self, current: str, target: str) -> bool:
        return target in self.transitions.get(current, frozenset())

    def move(self, obj: Any, target: str) -> None:
        if obj.state == target:
            return  # idempotent re-application of the same observation
        if not self.can(obj.state, target):
            raise TrollieError(
                ErrorCode.INVALID_STATE_TRANSITION,
                f"{self.name}: {obj.state} -> {target} not allowed",
                machine=self.name,
                current=obj.state,
                target=target,
            )
        obj.state = target
        obj.version += 1

    @property
    def states(self) -> set[str]:
        out = set(self.transitions)
        for targets in self.transitions.values():
            out |= targets
        return out


def _m(name: str, spec: dict[str, set[str]]) -> Machine:
    return Machine(name, {k: frozenset(v) for k, v in spec.items()})


ORDER = _m(
    "order",
    {
        "CREATED": {"PREPARING", "PAYMENT_PENDING", "CANCELLED"},
        "PREPARING": {"AWAITING_APPROVAL", "EXPIRED", "CANCELLED"},
        "AWAITING_APPROVAL": {"PAYMENT_PENDING", "EXPIRED", "CANCELLED"},
        "PAYMENT_PENDING": {
            "COMMITTING",
            "NEEDS_ATTENTION",
            "COMPENSATING",
            "CANCELLED",
            "EXPIRED",
        },
        "COMMITTING": {"FULFILLING", "NEEDS_ATTENTION", "COMPENSATING"},
        "NEEDS_ATTENTION": {"COMMITTING", "COMPENSATING", "CANCELLED", "FULFILLING"},
        "COMPENSATING": {"CANCELLED", "PARTIAL", "FULFILLING", "NEEDS_ATTENTION"},
        "FULFILLING": {"COMPLETED", "PARTIAL", "COMPENSATING", "DISPUTED"},
        "PARTIAL": {"COMPLETED", "COMPENSATING", "DISPUTED"},
        "COMPLETED": {"DISPUTED"},
        # A late successful debit after cancellation creates a refund obligation (§8.5).
        "CANCELLED": {"COMPENSATING"},
        "EXPIRED": {"COMPENSATING"},
    },
)

LEG = _m(
    "order_leg",
    {
        "DRAFT": {"RESERVED"},
        "RESERVED": {"COMMIT_REQUESTED", "CANCELLED"},
        "COMMIT_REQUESTED": {"ACCEPTED", "REJECTED", "UNKNOWN"},
        "UNKNOWN": {"ACCEPTED", "REJECTED"},
        "ACCEPTED": {"PICKING", "READY_FOR_COLLECTION", "CANCEL_REQUESTED", "FAILED"},
        "PICKING": {"READY_FOR_COLLECTION", "CANCEL_REQUESTED", "FAILED"},
        "READY_FOR_COLLECTION": {"COLLECTED", "CANCEL_REQUESTED", "FAILED"},
        "COLLECTED": {"DELIVERED", "FAILED"},
        "CANCEL_REQUESTED": {"CANCELLED", "ACCEPTED"},
    },
)

OPERATION = _m(
    "financial_operation",
    {
        "CREATED": {"SUBMITTED", "FAILED_FINAL"},
        "SUBMITTED": {"SUCCEEDED", "PENDING", "FAILED_FINAL", "UNKNOWN"},
        "PENDING": {"SUCCEEDED", "FAILED_FINAL", "UNKNOWN"},
        "UNKNOWN": {"RECONCILING", "SUCCEEDED", "FAILED_FINAL", "PENDING"},
        "RECONCILING": {"SUCCEEDED", "FAILED_FINAL", "PENDING", "UNKNOWN"},
    },
)

DELIVERY = _m(
    "delivery",
    {
        "QUOTED": {"BOOK_REQUESTED", "CANCELLED"},
        "BOOK_REQUESTED": {"BOOKED", "BOOKING_UNKNOWN", "FAILED"},
        "BOOKING_UNKNOWN": {"BOOKED", "FAILED"},
        "BOOKED": {"COLLECTING", "CANCEL_REQUESTED", "FAILED"},
        "COLLECTING": {"IN_TRANSIT", "FAILED"},
        "IN_TRANSIT": {"DELIVERED", "FAILED"},
        "CANCEL_REQUESTED": {"CANCELLED", "BOOKED"},
        "DELIVERED": {"DISPUTED"},
        "FAILED": {"DISPUTED"},
    },
)

REFUND = _m(
    "refund",
    {
        "REQUESTED": {"ASSESSED", "REJECTED_WITH_REASON"},
        "ASSESSED": {"APPROVED", "REJECTED_WITH_REASON"},
        "APPROVED": {"SUBMITTED"},
        "SUBMITTED": {"PROVIDER_CONFIRMED", "PENDING", "UNKNOWN", "FAILED_REQUIRES_ACTION"},
        "PENDING": {"PROVIDER_CONFIRMED", "UNKNOWN", "FAILED_REQUIRES_ACTION"},
        "UNKNOWN": {"PROVIDER_CONFIRMED", "PENDING", "FAILED_REQUIRES_ACTION"},
    },
)

MACHINES = (ORDER, LEG, OPERATION, DELIVERY, REFUND)

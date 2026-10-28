"""Payment adapter contract (blueprint §10.3). Only the restricted financial executor calls it."""

from dataclasses import dataclass
from typing import Any, Protocol


class PaymentTimeout(Exception):
    """No response. The provider may have acted; reconcile before any replacement."""


class IdempotencyConflict(Exception):
    """The provider saw this key with a different request."""


@dataclass(frozen=True)
class PaymentObservation:
    status: str  # requires_customer_action | authorised | succeeded | pending | failed | not_found
    provider_ref: str | None
    amount_minor: int | None = None
    reason: str | None = None
    checkout_url: str | None = None
    allocation: tuple[dict[str, Any], ...] = ()


class PaymentAdapter(Protocol):
    def create_checkout(
        self,
        *,
        idempotency_key: str,
        collection: str,
        amount_minor: int,
        reference: str,
        beneficiaries: list[dict[str, Any]],
    ) -> PaymentObservation: ...

    def capture(
        self,
        *,
        idempotency_key: str,
        authorisation_ref: str,
        amount_minor: int,
        beneficiaries: list[dict[str, Any]] | None = None,
    ) -> PaymentObservation: ...

    def void(self, *, idempotency_key: str, authorisation_ref: str) -> PaymentObservation: ...

    def refund(
        self, *, idempotency_key: str, payment_ref: str, amount_minor: int
    ) -> PaymentObservation: ...

    def query(self, *, idempotency_key: str) -> PaymentObservation: ...

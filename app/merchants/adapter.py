"""Merchant contract (blueprint §10.2). Real adapters and the simulator implement this."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


class MerchantTimeout(Exception):
    """No response received. The merchant may or may not have acted; look up by reference."""


@dataclass(frozen=True)
class ReservationLine:
    product_id: uuid.UUID
    merchant_sku: str
    units: int
    unit_price_minor: int


@dataclass(frozen=True)
class ReservationObservation:
    client_ref: str
    status: str  # held | rejected | released | consumed | expired | not_found
    merchant_ref: str | None = None
    expires_at: datetime | None = None
    reason: str | None = None


@dataclass(frozen=True)
class OrderObservation:
    client_ref: str
    status: str  # accepted | rejected | cancelled | ready | not_found
    merchant_ref: str | None = None
    reason: str | None = None
    lines: tuple[dict[str, Any], ...] = ()


class MerchantAdapter(Protocol):
    def prepare_reservation(
        self, *, location_id: uuid.UUID, client_ref: str, lines: list[ReservationLine]
    ) -> ReservationObservation: ...

    def get_reservation(self, *, client_ref: str) -> ReservationObservation: ...

    def release_reservation(self, *, client_ref: str) -> ReservationObservation: ...

    def commit_order(
        self, *, location_id: uuid.UUID, client_ref: str, reservation_ref: str
    ) -> OrderObservation: ...

    def get_order(self, *, client_ref: str) -> OrderObservation: ...

    def cancel_order(self, *, client_ref: str) -> OrderObservation: ...

    def mark_ready(self, *, client_ref: str) -> OrderObservation: ...

    # TODO(blueprint §10.2): propose_substitution, get_receipt and resolve_issue are part of
    # the contract but not exercised in this sprint; substitutions require fresh approval.

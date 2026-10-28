"""Simulated merchant implementing the merchant contract (blueprint §10.2).

Fault modes per operation:
- `reject`: refuse the request;
- `timeout_after_effect`: perform the action, then raise MerchantTimeout (response lost);
- `timeout_before_effect`: raise MerchantTimeout without acting;
- `lose_stock` (commit_order): a held reservation turns out to be unfulfilable (T10).
"""

import uuid
from dataclasses import asdict
from datetime import timedelta

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.clock import Clock
from app.merchants.adapter import (
    MerchantTimeout,
    OrderObservation,
    ReservationLine,
    ReservationObservation,
)
from app.offers.models import OfferVersion
from app.simulators.faults import take
from app.simulators.models import SimMerchantOrder, SimMerchantReservation, SimMerchantStock

DEFAULT_TTL = timedelta(minutes=30)
UNLIMITED = 1000


class SimulatedMerchant:
    def __init__(self, engine: Engine, clock: Clock, ttl: timedelta = DEFAULT_TTL) -> None:
        self.engine = engine
        self.clock = clock
        self.ttl = ttl

    # --- helpers ---------------------------------------------------------------------

    def _fault(self, s: Session, location_id: uuid.UUID, operation: str) -> str | None:
        return take(s, system="merchant", target=str(location_id), operation=operation)

    def _stock(self, s: Session, location_id: uuid.UUID, product_id: uuid.UUID) -> SimMerchantStock:
        row = s.get(SimMerchantStock, (location_id, product_id), with_for_update=True)
        if row is None:
            observed = s.scalars(
                select(OfferVersion.stock_quantity)
                .where(
                    OfferVersion.location_id == location_id, OfferVersion.product_id == product_id
                )
                .order_by(OfferVersion.observed_at.desc())
                .limit(1)
            ).first()
            row = SimMerchantStock(
                location_id=location_id,
                product_id=product_id,
                on_hand=UNLIMITED if observed is None else observed,
            )
            s.add(row)
            s.flush()
        return row

    def _expire(self, s: Session, res: SimMerchantReservation) -> None:
        if res.state == "held" and res.expires_at <= self.clock.now():
            for line in res.lines:
                self._stock(s, res.location_id, uuid.UUID(line["product_id"])).held -= line["units"]
            res.state = "expired"

    @staticmethod
    def _res_obs(res: SimMerchantReservation | None, client_ref: str) -> ReservationObservation:
        if res is None:
            return ReservationObservation(client_ref, "not_found")
        return ReservationObservation(client_ref, res.state, res.merchant_ref, res.expires_at)

    @staticmethod
    def _order_obs(order: SimMerchantOrder | None, client_ref: str) -> OrderObservation:
        if order is None:
            return OrderObservation(client_ref, "not_found")
        return OrderObservation(
            client_ref, order.state, order.merchant_ref, order.reason, tuple(order.lines)
        )

    # --- contract --------------------------------------------------------------------

    def prepare_reservation(self, *, location_id, client_ref, lines: list[ReservationLine]):
        with Session(self.engine) as s, s.begin():
            existing = s.get(SimMerchantReservation, client_ref)
            if existing is not None:  # deduplicated by client reference
                self._expire(s, existing)
                return self._res_obs(existing, client_ref)
            fault = self._fault(s, location_id, "prepare_reservation")
            if fault == "timeout_before_effect":
                raise MerchantTimeout(client_ref)
            if fault == "reject":
                return ReservationObservation(client_ref, "rejected", reason="merchant_declined")
            for line in lines:
                stock = self._stock(s, location_id, line.product_id)
                if stock.on_hand - stock.held < line.units:
                    return ReservationObservation(
                        client_ref, "rejected", reason="insufficient_stock"
                    )
            for line in lines:
                self._stock(s, location_id, line.product_id).held += line.units
            res = SimMerchantReservation(
                client_ref=client_ref,
                merchant_ref=f"SIMRES-{uuid.uuid4().hex[:10]}",
                location_id=location_id,
                lines=[{**asdict(ln), "product_id": str(ln.product_id)} for ln in lines],
                state="held",
                expires_at=self.clock.now() + self.ttl,
            )
            s.add(res)
            s.flush()
            observation = self._res_obs(res, client_ref)
        if fault == "timeout_after_effect":
            raise MerchantTimeout(client_ref)
        return observation

    def get_reservation(self, *, client_ref):
        with Session(self.engine) as s, s.begin():
            res = s.get(SimMerchantReservation, client_ref, with_for_update=True)
            if res is not None:
                self._expire(s, res)
            return self._res_obs(res, client_ref)

    def release_reservation(self, *, client_ref):
        with Session(self.engine) as s, s.begin():
            res = s.get(SimMerchantReservation, client_ref, with_for_update=True)
            if res is None:
                return self._res_obs(None, client_ref)
            self._expire(s, res)
            if res.state == "held":
                for line in res.lines:
                    self._stock(s, res.location_id, uuid.UUID(line["product_id"])).held -= line[
                        "units"
                    ]
                res.state = "released"
            return self._res_obs(res, client_ref)

    def commit_order(self, *, location_id, client_ref, reservation_ref):
        with Session(self.engine) as s, s.begin():
            existing = s.get(SimMerchantOrder, client_ref)
            if existing is not None:  # deduplicated by client reference
                return self._order_obs(existing, client_ref)
            fault = self._fault(s, location_id, "commit_order")
            if fault == "timeout_before_effect":
                raise MerchantTimeout(client_ref)
            res = s.scalars(
                select(SimMerchantReservation)
                .where(SimMerchantReservation.merchant_ref == reservation_ref)
                .with_for_update()
            ).one_or_none()
            if res is not None:
                self._expire(s, res)
            reason = None
            if fault == "reject":
                reason = "merchant_declined"
            elif fault == "lose_stock":
                reason = "stock_lost"
            elif res is None or res.state != "held":
                reason = "reservation_not_held"
            order = SimMerchantOrder(
                client_ref=client_ref,
                merchant_ref=f"SIMORD-{uuid.uuid4().hex[:10]}",
                location_id=location_id,
                reservation_ref=reservation_ref,
                lines=list(res.lines) if res else [],
                state="rejected" if reason else "accepted",
                reason=reason,
            )
            if reason is None:
                for line in res.lines:
                    stock = self._stock(s, location_id, uuid.UUID(line["product_id"]))
                    stock.held -= line["units"]
                    stock.on_hand -= line["units"]
                res.state = "consumed"
            elif res is not None and res.state == "held" and fault in ("reject", "lose_stock"):
                for line in res.lines:
                    self._stock(s, location_id, uuid.UUID(line["product_id"])).held -= line["units"]
                res.state = "released"
            s.add(order)
            s.flush()
            observation = self._order_obs(order, client_ref)
        if fault == "timeout_after_effect":
            raise MerchantTimeout(client_ref)
        return observation

    def get_order(self, *, client_ref):
        with Session(self.engine) as s:
            return self._order_obs(s.get(SimMerchantOrder, client_ref), client_ref)

    def cancel_order(self, *, client_ref):
        with Session(self.engine) as s, s.begin():
            order = s.get(SimMerchantOrder, client_ref, with_for_update=True)
            if order is not None and order.state == "accepted":
                for line in order.lines:
                    self._stock(
                        s, order.location_id, uuid.UUID(line["product_id"])
                    ).on_hand += line["units"]
                order.state = "cancelled"
            return self._order_obs(order, client_ref)

    def mark_ready(self, *, client_ref):
        with Session(self.engine) as s, s.begin():
            order = s.get(SimMerchantOrder, client_ref, with_for_update=True)
            if order is not None and order.state == "accepted":
                order.state = "ready"
            return self._order_obs(order, client_ref)

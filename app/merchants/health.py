"""Merchant integration health: a circuit breaker per location (I-045).

A merchant whose integration keeps timing out is temporarily left out of new baskets, so
shoppers get a basket from a store that answers instead of waiting for one that does not.
Orders already placed are unaffected: their calls still go through (and are reconciled by
lookup as usual). In-process state; a multi-process deployment would share it.
"""

import threading
import time
import uuid
from collections import deque

from app.config import get_settings
from app.merchants.adapter import MerchantTimeout


class HealthCheckedMerchant:
    def __init__(self, inner) -> None:
        self.inner = inner
        self._lock = threading.Lock()
        self._failures: dict[uuid.UUID, deque[float]] = {}
        self._open_until: dict[uuid.UUID, float] = {}
        self._location_of: dict[str, uuid.UUID] = {}
        self.opened: list[tuple[float, uuid.UUID]] = []  # history, for reports

    def unavailable(self) -> frozenset[uuid.UUID]:
        now = time.monotonic()
        with self._lock:
            return frozenset(loc for loc, until in self._open_until.items() if until > now)

    def _record(self, location_id: uuid.UUID | None, failed: bool) -> None:
        if location_id is None or not failed:
            return
        cfg = get_settings()
        now = time.monotonic()
        with self._lock:
            q = self._failures.setdefault(location_id, deque())
            q.append(now)
            while q and q[0] < now - cfg.merchant_circuit_window_s:
                q.popleft()
            if (
                len(q) >= cfg.merchant_circuit_failures
                and self._open_until.get(location_id, 0) < now
            ):
                self._open_until[location_id] = now + cfg.merchant_circuit_open_s
                self.opened.append((time.time(), location_id))
                q.clear()

    def _call(self, loc, fn, **kw):
        try:
            return fn(**kw)
        except MerchantTimeout:
            self._record(loc, True)
            raise

    def prepare_reservation(self, *, location_id, client_ref, lines):
        self._location_of[client_ref] = location_id
        return self._call(location_id, self.inner.prepare_reservation,
                          location_id=location_id, client_ref=client_ref, lines=lines)  # fmt: skip

    def commit_order(self, *, location_id, client_ref, reservation_ref):
        self._location_of[client_ref] = location_id
        return self._call(location_id, self.inner.commit_order, location_id=location_id,
                          client_ref=client_ref, reservation_ref=reservation_ref)  # fmt: skip

    def get_reservation(self, *, client_ref):
        return self._call(self._location_of.get(client_ref), self.inner.get_reservation,
                          client_ref=client_ref)  # fmt: skip

    def release_reservation(self, *, client_ref):
        return self._call(self._location_of.get(client_ref), self.inner.release_reservation,
                          client_ref=client_ref)  # fmt: skip

    def get_order(self, *, client_ref):
        return self._call(self._location_of.get(client_ref), self.inner.get_order,
                          client_ref=client_ref)  # fmt: skip

    def cancel_order(self, *, client_ref):
        return self._call(self._location_of.get(client_ref), self.inner.cancel_order,
                          client_ref=client_ref)  # fmt: skip

    def mark_ready(self, *, client_ref):
        return self.inner.mark_ready(client_ref=client_ref)

"""Everything outside Trollie: banks, merchants' staff, couriers and bad luck."""

import asyncio
import random
import time

from scripts.crowd.actions import Board
from scripts.crowd.api import Api

MERCHANT_FAULTS = [
    ("commit_order", "reject"),
    ("commit_order", "timeout_after_effect"),
    ("commit_order", "timeout_before_effect"),
    ("commit_order", "lose_stock"),
    ("prepare_reservation", "timeout_after_effect"),
    ("prepare_reservation", "reject"),
]
PAYMENT_FAULTS = [
    ("capture", "timeout_after_effect"),
    ("capture", "timeout_before_effect"),
    ("create_checkout", "timeout_after_effect"),
    ("customer_completes", "duplicate_webhook"),
    ("customer_completes", "delay_webhook"),
    ("refund", "timeout_after_effect"),
    ("void", "timeout_before_effect"),
]
COURIER_FAULTS = [("book", "timeout_after_effect"), ("book", "reject")]


class World:
    def __init__(self, api: Api, board: Board, rng: random.Random, chaos: float) -> None:
        self.api = api
        self.board = board
        self.rng = rng
        self.chaos = chaos
        self.faults_armed: list[str] = []
        self.deliveries = {"ready": 0, "delivered": 0, "failed": 0}
        self.transfers_sent = 0
        self.settlements: list[dict] = []
        self.errors: list[str] = []

    async def run(self, stop: asyncio.Event, locations: list[str]) -> None:
        await asyncio.gather(
            self._bank(stop), self._fulfil(stop), self._chaos(stop, locations), self._settle(stop)
        )

    async def _bank(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            now = time.monotonic()
            due = [t for t in self.board.transfers if t[0] <= now]
            for item in due:
                self.board.transfers.remove(item)
                r = await self.api.call("POST", "/v1/dev/sim/transfers", json=item[1])
                self.transfers_sent += 1
                if not r.ok:
                    self.errors.append(
                        f"bank transfer -> {r.status or r.error}: {str(r.body)[:200]}"
                    )
            await asyncio.sleep(1)

    async def _fulfil(self, stop: asyncio.Event) -> None:
        """Store staff mark legs ready; couriers collect and deliver (sometimes fail)."""
        while not stop.is_set():
            for _, oid in list(self.board.orders):
                r = await self.api.call("GET", f"/v1/dev/orders/{oid}/fulfilment")
                if not r.ok:
                    if r.status is None or r.status >= 500:
                        self.errors.append(f"fulfilment {oid[:8]} -> {r.status or r.error}")
                    continue
                for leg in r.body["legs"]:
                    if self.rng.random() < 0.5:
                        continue  # not everyone is quick
                    job = leg["delivery_job_id"]
                    if leg["state"] == "ACCEPTED":
                        x = await self.api.call(
                            "POST", f"/v1/dev/merchant/legs/{leg['order_leg_id']}/ready"
                        )
                        self.deliveries["ready"] += x.ok
                    elif (
                        job
                        and leg["state"] == "READY_FOR_COLLECTION"
                        and leg["delivery_state"] == "BOOKED"
                    ):
                        await self.api.call("POST", f"/v1/dev/courier/jobs/{job}/collected")
                    elif job and leg["state"] == "COLLECTED":
                        to = "failed" if self.rng.random() < 0.05 else "delivered"
                        x = await self.api.call("POST", f"/v1/dev/courier/jobs/{job}/{to}")
                        self.deliveries[to] += x.ok
            await asyncio.sleep(3)

    async def _chaos(self, stop: asyncio.Event, locations: list[str]) -> None:
        while not stop.is_set():
            await asyncio.sleep(self.rng.expovariate(1 / 8))
            if self.rng.random() > self.chaos:
                continue
            system = self.rng.choices(["merchant", "payment", "courier"], [5, 4, 1])[0]
            if system == "merchant":
                op, mode = self.rng.choice(MERCHANT_FAULTS)
                target = self.rng.choice(locations)
            elif system == "payment":
                op, mode = self.rng.choice(PAYMENT_FAULTS)
                target = op
            else:
                op, mode = self.rng.choice(COURIER_FAULTS)
                target = "book"
            r = await self.api.call(
                "POST",
                "/v1/dev/sim/faults",
                json={"system": system, "target": target, "operation": op, "mode": mode},
            )
            if r.ok:
                self.faults_armed.append(f"{system}:{op}:{mode}")

    async def _settle(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            await asyncio.sleep(45)
            r = await self.api.call("POST", "/v1/dev/settlement-reports")
            if r.ok:
                self.settlements.append(r.body)
            else:
                self.errors.append(f"settlement -> {r.status}: {str(r.body)[:200]}")

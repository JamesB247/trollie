"""Everything outside Trollie: banks, merchants' staff, couriers, thieves and bad luck."""

import asyncio
import random
import time
from datetime import UTC, datetime

from app.simulators.bigmarket import CHAINS as BIG_CHAINS
from app.simulators.bigmarket import location_id as big_location_id
from scripts.crowd.actions import Board
from scripts.crowd.api import INFO, Api, Log

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

# How each merchant's staff and couriers behave once an order is accepted.
#   ready_p: chance per tick that staff mark an accepted leg ready (never, for the scam)
#   late_p:  chance a leg's courier arrives after the delivery window, and by how much
BEHAVIOUR = {
    "ubuntu": {"ready_p": 0.6, "late_p": 0.05, "late_s": (20, 90)},
    "zest": {"ready_p": 0.9, "late_p": 0.55, "late_s": (60, 240)},
    "fairbasket": {"ready_p": 0.6, "late_p": 0.05, "late_s": (20, 90)},
    "kaya": {"ready_p": 0.3, "late_p": 0.1, "late_s": (60, 180)},
    "bargainbox": {"ready_p": 0.0, "late_p": 0.0, "late_s": (0, 0)},
}
DEFAULT_BEHAVIOUR = {"ready_p": 0.5, "late_p": 0.05, "late_s": (20, 90)}
CHAIN_OF = {str(big_location_id(b.code)): c.code for c in BIG_CHAINS for b in c.branches}


class World:
    def __init__(
        self, api: Api, board: Board, rng: random.Random, chaos: float, log: Log | None = None
    ) -> None:
        self.api = api
        self.board = board
        self.rng = rng
        self.chaos = chaos
        self.log = log
        self.faults_armed: list[str] = []
        self.deliveries = {"ready": 0, "delivered": 0, "late": 0, "failed": 0}
        self.transfers_sent = {"confirmed": 0, "reversed": 0, "other": 0}
        self.settlements: list[dict] = []
        self.errors: list[str] = []
        self.timeline: list[tuple[float, str]] = []  # (sim hour, what happened)
        self._late: dict[str, float] = {}  # order_leg_id -> courier arrival (unix seconds)
        self._started = time.monotonic()
        self._done: set[str] = set()

    def note(self, what: str) -> None:
        self.timeline.append((self.log.hour() if self.log else 0.0, what))

    async def run(self, stop: asyncio.Event, locations: list[str], hijack_at: float) -> None:
        await asyncio.gather(
            self._bank(stop),
            self._fulfil(stop),
            self._chaos(stop, locations),
            self._settle(stop),
            self._hijack(stop, hijack_at),
        )

    async def _bank(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            now = time.monotonic()
            due = [t for t in self.board.transfers if t[0] <= now]
            for item in due:
                self.board.transfers.remove(item)
                r = await self.api.call("POST", "/v1/dev/sim/transfers", json=item[1])
                kind = item[1].get("status", "confirmed")
                self.transfers_sent[kind if kind in self.transfers_sent else "other"] += 1
                if kind == "reversed":
                    self.note(f"bank recalls a stolen R{item[1]['amount_minor'] / 100:,.0f} top-up")
                if not r.ok:
                    self.errors.append(
                        f"bank transfer -> {r.status or r.error}: {str(r.body)[:200]}"
                    )
            await asyncio.sleep(1)

    def _behaviour(self, location_id: str) -> dict:
        return BEHAVIOUR.get(CHAIN_OF.get(location_id, ""), DEFAULT_BEHAVIOUR)

    async def _fulfil(self, stop: asyncio.Event) -> None:
        """Store staff mark legs ready; couriers collect and deliver, some of them late."""
        while not stop.is_set():
            for shopper, oid in list(self.board.orders):
                if oid in self._done:
                    continue
                r = await self.api.call("GET", f"/v1/dev/orders/{oid}/fulfilment")
                if not r.ok:
                    if r.status is None or r.status >= 500:
                        self.errors.append(f"fulfilment {oid[:8]} -> {r.status or r.error}")
                    continue
                if r.body["state"] in ("COMPLETED", "CANCELLED", "EXPIRED", "PARTIAL"):
                    self._done.add(oid)
                    continue
                quote_legs = {
                    leg["leg_id"]: leg for leg in shopper.order_quotes.get(oid, {}).get("legs", [])
                }
                for leg in r.body["legs"]:
                    q = quote_legs.get(leg["leg_id"])
                    if q is None:
                        continue
                    b = self._behaviour(q["location_id"])
                    job = leg["delivery_job_id"]
                    if leg["state"] == "ACCEPTED":
                        if self.rng.random() < b["ready_p"]:
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
                        arrive = self._arrival(leg["order_leg_id"], q, b)
                        if time.time() < arrive:
                            continue
                        to = "failed" if self.rng.random() < 0.04 else "delivered"
                        x = await self.api.call("POST", f"/v1/dev/courier/jobs/{job}/{to}")
                        if x.ok:
                            self.deliveries[to] += 1
                            end = datetime.fromisoformat(q["window_end"]).timestamp()
                            self.deliveries["late"] += to == "delivered" and time.time() > end
            await asyncio.sleep(2)

    def _arrival(self, order_leg_id: str, q: dict, b: dict) -> float:
        if order_leg_id not in self._late:
            start = datetime.fromisoformat(q["window_start"]).timestamp()
            end = datetime.fromisoformat(q["window_end"]).timestamp()
            if self.rng.random() < b["late_p"]:
                self._late[order_leg_id] = end + self.rng.uniform(*b["late_s"])
            else:
                self._late[order_leg_id] = self.rng.uniform(start, end)
        return self._late[order_leg_id]

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

    async def _hijack(self, stop: asyncio.Event, at: float) -> None:
        """A phishing link or a compromised phone: someone's agent token is stolen."""
        while not stop.is_set() and time.monotonic() < at:
            await asyncio.sleep(1)
        pending = [s for s in self.board.shoppers if "hijacks_agents" in s.p.archetype.traits]
        give_up = time.monotonic() + (at - self._started) * 1.5  # until ~75% of the day
        while pending and not stop.is_set() and time.monotonic() < give_up:
            victims = [
                s
                for s in self.board.shoppers
                if s.agent_token and s.grant_id and not any(h[0] is s for h in self.board.hijacked)
            ]
            if not victims:
                await asyncio.sleep(2)  # wait for someone to set up an agent
                continue
            thief = pending.pop()
            v = self.rng.choice(victims)
            thief.stolen = (v, v.agent_token, v.agent_id, v.envelope_id)
            self.board.hijacked.append((v, thief, datetime.now(UTC)))
            self.note(f"{thief.name} hijacks {v.name}'s shopping agent")
            if self.log:
                self.log.add(
                    user=thief.name, archetype="hijacker", brain="world", said="",
                    action="agent_token_stolen", status=None, code=None, verdict=INFO,
                    detail=f"stole the agent of {v.name}", ms=0,
                )  # fmt: skip
        for thief in pending:
            self.note(f"{thief.name} found no agent to hijack")

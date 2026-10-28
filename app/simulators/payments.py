"""Simulated payment provider ("simpay"). SIMULATED — NOT REAL MONEY.

Behaviour that matters for Trollie's controls:
- Idempotency keys are honoured for `retention` only (like a real provider's horizon).
  Within it, an identical retry replays the original result; a different request with
  the same key is rejected. After it, the key is forgotten and a replay would create a
  second charge — which is why Trollie blocks automatic replay beyond the horizon (T27).
- Results are announced by signed webhooks from the provider's own queue.
- The customer completes hosted checkout or the bank-app step via `customer_completes`.

Fault modes (system="payment", target=operation): timeout_after_effect,
timeout_before_effect, decline, duplicate_webhook, delay_webhook, drop_webhook,
conflicting_lookup.
"""

import json
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.clock import Clock
from app.durable.hashing import canonical_hash
from app.durable.inbox import sign
from app.payments.adapter import IdempotencyConflict, PaymentObservation, PaymentTimeout
from app.simulators.faults import take
from app.simulators.models import SimIdempotencyKey, SimPayment, SimWebhook

ACCOUNT = "sim-acct-1"


def _has(fault: str | None, mode: str) -> bool:
    """Fault modes combine with '+', e.g. 'timeout_after_effect+drop_webhook'."""
    return fault is not None and mode in fault.split("+")


class SimulatedPaymentProvider:
    def __init__(
        self,
        engine: Engine,
        clock: Clock,
        *,
        secret: bytes,
        environment: str,
        retention: timedelta = timedelta(hours=24),
    ) -> None:
        self.engine = engine
        self.clock = clock
        self.secret = secret
        self.environment = environment
        self.retention = retention

    # --- internals -------------------------------------------------------------------

    def _fault(self, s: Session, operation: str) -> str | None:
        return take(s, system="payment", target=operation, operation=operation)

    def _remembered(self, s: Session, key: str, request: dict[str, Any]) -> SimPayment | None:
        known = s.get(SimIdempotencyKey, key, with_for_update=True)
        if known is None:
            return None
        if known.created_at + self.retention < self.clock.now():
            s.delete(known)  # forgotten: the provider will treat a replay as new
            s.flush()
            return None
        if known.request_hash != canonical_hash(request):
            raise IdempotencyConflict(key)
        return s.get(SimPayment, known.provider_ref)

    def _remember(self, s: Session, key: str, request: dict[str, Any], payment: SimPayment):
        s.add(
            SimIdempotencyKey(
                key=key,
                request_hash=canonical_hash(request),
                provider_ref=payment.provider_ref,
                created_at=self.clock.now(),
            )
        )

    def _emit(
        self, s: Session, event_type: str, payment: SimPayment, fault: str | None, **extra: Any
    ) -> None:
        if _has(fault, "drop_webhook"):
            return
        event_id = f"evt_{uuid.uuid4().hex}"
        body = json.dumps(
            {
                "id": event_id,
                "type": event_type,
                "account": ACCOUNT,
                "environment": self.environment,
                "data": {
                    "provider_ref": payment.provider_ref,
                    "client_key": payment.client_key,
                    "status": payment.status,
                    "amount_minor": payment.amount_minor,
                    "parent_ref": payment.parent_ref,
                    "reference": payment.reference,
                    **extra,
                },
            }
        )
        delay = timedelta(minutes=10) if _has(fault, "delay_webhook") else timedelta(0)
        s.add(
            SimWebhook(
                event_id=event_id,
                body=body,
                deliver_after=self.clock.now() + delay,
                deliveries_remaining=2 if _has(fault, "duplicate_webhook") else 1,
            )
        )

    @staticmethod
    def _obs(p: SimPayment, **kw: Any) -> PaymentObservation:
        return PaymentObservation(
            status=p.status, provider_ref=p.provider_ref, amount_minor=p.amount_minor, **kw
        )

    def _new(
        self, s: Session, kind: str, *, client_key: str, amount: int, status: str, **kw: Any
    ) -> SimPayment:
        p = SimPayment(
            provider_ref=f"sim_{kind}_{uuid.uuid4().hex[:12]}",
            kind=kind,
            client_key=client_key,
            amount_minor=amount,
            status=status,
            created_at=self.clock.now(),
            **kw,
        )
        s.add(p)
        s.flush()
        return p

    def _run(self, operation: str, key: str, request: dict[str, Any], act):
        with Session(self.engine) as s, s.begin():
            replay = self._remembered(s, key, request)
            if replay is not None:
                return self._obs(replay)
            fault = self._fault(s, operation)
            if _has(fault, "timeout_before_effect"):
                raise PaymentTimeout(key)
            payment = act(s, fault)
            self._remember(s, key, request, payment)
            observation = self._obs(
                payment,
                checkout_url=(
                    f"sim://checkout/{payment.provider_ref}" if payment.kind == "checkout" else None
                ),
            )
        if _has(fault, "timeout_after_effect"):
            raise PaymentTimeout(key)
        return observation

    # --- contract --------------------------------------------------------------------

    def create_checkout(
        self, *, idempotency_key, collection, amount_minor, reference, beneficiaries
    ):
        request = {
            "op": "checkout",
            "collection": collection,
            "amount": amount_minor,
            "reference": reference,
            "beneficiaries": beneficiaries,
        }

        def act(s, fault):
            return self._new(
                s,
                "checkout",
                client_key=idempotency_key,
                amount=amount_minor,
                status="requires_customer_action",
                collection=collection,
                reference=reference,
                beneficiaries=beneficiaries,
            )

        return self._run("create_checkout", idempotency_key, request, act)

    def capture(self, *, idempotency_key, authorisation_ref, amount_minor, beneficiaries=None):
        request = {
            "op": "capture",
            "auth": authorisation_ref,
            "amount": amount_minor,
            "beneficiaries": beneficiaries,
        }

        def act(s, fault):
            auth = s.get(SimPayment, authorisation_ref, with_for_update=True)
            allocation = (
                beneficiaries if beneficiaries is not None else (auth.beneficiaries if auth else [])
            )
            if (
                auth is None
                or auth.status != "authorised"
                or amount_minor > auth.amount_minor
                or sum(b["gross_minor"] for b in allocation) != amount_minor
            ):
                return self._new(
                    s,
                    "capture",
                    client_key=idempotency_key,
                    amount=amount_minor,
                    status="failed",
                    parent_ref=authorisation_ref,
                )
            auth.status = "captured"
            auth.captured_minor = amount_minor
            cap = self._new(
                s,
                "capture",
                client_key=idempotency_key,
                amount=amount_minor,
                status="succeeded",
                parent_ref=authorisation_ref,
                beneficiaries=allocation,
                reference=auth.reference,
            )
            self._emit(s, "payment.captured", cap, fault)
            return cap

        return self._run("capture", idempotency_key, request, act)

    def void(self, *, idempotency_key, authorisation_ref):
        request = {"op": "void", "auth": authorisation_ref}

        def act(s, fault):
            auth = s.get(SimPayment, authorisation_ref, with_for_update=True)
            if auth is None or auth.status not in ("authorised", "requires_customer_action"):
                return self._new(
                    s,
                    "void",
                    client_key=idempotency_key,
                    amount=1,
                    status="failed",
                    parent_ref=authorisation_ref,
                )
            auth.status = "voided"
            v = self._new(
                s,
                "void",
                client_key=idempotency_key,
                amount=auth.amount_minor,
                status="succeeded",
                parent_ref=authorisation_ref,
                reference=auth.reference,
            )
            self._emit(s, "payment.voided", v, fault)
            return v

        return self._run("void", idempotency_key, request, act)

    def refund(self, *, idempotency_key, payment_ref, amount_minor):
        request = {"op": "refund", "payment": payment_ref, "amount": amount_minor}

        def act(s, fault):
            paid = s.get(SimPayment, payment_ref, with_for_update=True)
            source = paid
            if paid is not None and paid.kind == "capture":
                source = s.get(SimPayment, paid.parent_ref, with_for_update=True)
            refundable = (
                0
                if source is None
                else (
                    (
                        source.captured_minor
                        if source.collection == "auth_capture"
                        else source.amount_minor
                    )
                    - source.refunded_minor
                )
            )
            if source is None or amount_minor > refundable:
                return self._new(
                    s,
                    "refund",
                    client_key=idempotency_key,
                    amount=amount_minor,
                    status="failed",
                    parent_ref=payment_ref,
                )
            source.refunded_minor += amount_minor
            # Proportional reversal across the original beneficiaries (cf. blueprint §2.3),
            # largest-remainder rounding, never more than a beneficiary has left.
            already: dict[str, int] = {}
            for r in s.scalars(
                select(SimPayment).where(
                    SimPayment.kind == "refund",
                    SimPayment.parent_ref == payment_ref,
                    SimPayment.status == "succeeded",
                )
            ):
                for part in r.beneficiaries:
                    already[part["beneficiary"]] = (
                        already.get(part["beneficiary"], 0) + part["reversed_minor"]
                    )
            left = {
                b["beneficiary"]: b["gross_minor"] - already.get(b["beneficiary"], 0)
                for b in source.beneficiaries
            }
            pool = sum(left.values()) or 1
            shares = {k: amount_minor * v // pool for k, v in left.items()}
            remainder = amount_minor - sum(shares.values())
            for k in sorted(left, key=lambda k: (-(amount_minor * left[k] % pool), k)):
                if remainder == 0:
                    break
                if shares[k] < left[k]:
                    shares[k] += 1
                    remainder -= 1
            allocation = [{"beneficiary": k, "reversed_minor": v} for k, v in shares.items()]
            status = "pending" if _has(fault, "decline") else "succeeded"
            r = self._new(
                s,
                "refund",
                client_key=idempotency_key,
                amount=amount_minor,
                status=status,
                parent_ref=payment_ref,
                beneficiaries=allocation,
                reference=source.reference,
            )
            self._emit(
                s,
                "refund.succeeded" if status == "succeeded" else "refund.pending",
                r,
                fault,
                allocation=allocation,
            )
            return r

        return self._run("refund", idempotency_key, request, act)

    def query(self, *, idempotency_key):
        with Session(self.engine) as s, s.begin():
            fault = self._fault(s, "query")
            if _has(fault, "timeout_before_effect"):
                raise PaymentTimeout(idempotency_key)
            known = s.get(SimIdempotencyKey, idempotency_key)
            if known is None or known.created_at + self.retention < self.clock.now():
                return PaymentObservation(status="not_found", provider_ref=None)
            p = s.get(SimPayment, known.provider_ref)
            if _has(fault, "conflicting_lookup"):
                return PaymentObservation(
                    status="failed",
                    provider_ref=p.provider_ref,
                    amount_minor=p.amount_minor,
                    reason="lookup_disagrees",
                )
            return self._obs(p, allocation=tuple(p.beneficiaries))

    # --- the customer's side and the provider's own outbound queue ------------------------

    def customer_completes(self, provider_ref: str, *, approve: bool = True) -> None:
        """The customer finishes 3DS / the bank-app step (never intercepted by Trollie)."""
        with Session(self.engine) as s, s.begin():
            p = s.get(SimPayment, provider_ref, with_for_update=True)
            if p is None or p.status != "requires_customer_action":
                return
            fault = self._fault(s, "customer_completes")
            if not approve or _has(fault, "decline"):
                p.status = "failed"
                self._emit(s, "payment.failed", p, fault)
            elif p.collection == "auth_capture":
                p.status = "authorised"
                self._emit(s, "payment.authorised", p, fault)
            else:
                p.status = "succeeded"
                self._emit(s, "payment.succeeded", p, fault)

    def deliver_webhooks(self, deliver) -> int:
        """Send due webhooks to `deliver(body, signature, timestamp)`. Returns count sent."""
        sent = 0
        with Session(self.engine) as s, s.begin():
            due = s.scalars(
                select(SimWebhook)
                .where(
                    SimWebhook.deliver_after <= self.clock.now(),
                    SimWebhook.deliveries_remaining > 0,
                )
                .order_by(SimWebhook.deliver_after, SimWebhook.created_at)
            ).all()
            batch = []
            for hook in due:
                for _ in range(hook.deliveries_remaining):
                    batch.append(hook.body)
                hook.deliveries_remaining = 0
        for body in batch:
            ts = int(self.clock.now().timestamp())
            raw = body.encode()
            deliver(raw, sign(self.secret, ts, raw), str(ts))
            sent += 1
        return sent

    def settlement_report(self, report_ref: str) -> dict:
        """Settle every collected, unsettled payment: one payout line per beneficiary, net of
        refund reversals, plus a separate provider-fee line (1.5%, invented) charged to the
        platform."""
        lines = []
        with Session(self.engine) as s, s.begin():
            fail_next = take(s, system="payment", target="settlement", operation="payout")
            paid = s.scalars(
                select(SimPayment)
                .where(
                    SimPayment.settled.is_(False),
                    SimPayment.status == "succeeded",
                    (
                        (SimPayment.kind == "capture")
                        | ((SimPayment.kind == "checkout") & (SimPayment.collection == "immediate"))
                    ),
                )
                .order_by(SimPayment.created_at, SimPayment.provider_ref)
                .with_for_update()
            ).all()
            for p in paid:
                reversed_by: dict[str, int] = {}
                for r in s.scalars(
                    select(SimPayment).where(
                        SimPayment.kind == "refund",
                        SimPayment.parent_ref == p.provider_ref,
                        SimPayment.status == "succeeded",
                    )
                ):
                    for part in r.beneficiaries:
                        reversed_by[part["beneficiary"]] = (
                            reversed_by.get(part["beneficiary"], 0) + part["reversed_minor"]
                        )
                for b in p.beneficiaries:
                    gross = b["gross_minor"] - reversed_by.get(b["beneficiary"], 0)
                    if gross == 0:
                        continue
                    kind = "payout"
                    if fail_next == "payout_failed" and b["beneficiary"].startswith("merchant:"):
                        kind, fail_next = "payout_failed", None
                    lines.append(
                        {
                            "line_ref": f"{report_ref}:{p.provider_ref}:{b['beneficiary']}",
                            "operation_ref": p.provider_ref,
                            "beneficiary": b["beneficiary"],
                            "kind": kind,
                            "gross_minor": gross,
                            "fee_minor": 0,
                            "net_minor": gross,
                            "settled_at": self.clock.now().isoformat(),
                        }
                    )
                # The provider keeps its fee even when the payment is later refunded.
                lines.append(
                    {
                        "line_ref": f"{report_ref}:{p.provider_ref}:fee",
                        "operation_ref": p.provider_ref,
                        "beneficiary": "platform",
                        "kind": "fee",
                        "gross_minor": 0,
                        "fee_minor": p.amount_minor * 150 // 10_000,
                        "net_minor": 0,
                        "settled_at": self.clock.now().isoformat(),
                    }
                )
                p.settled = True
        return {"provider": "simpay", "report_ref": report_ref, "lines": lines}

    def incoming_transfer(
        self,
        *,
        transfer_ref: str,
        reference: str,
        amount_minor: int,
        status: str = "confirmed",
        currency: str = "ZAR",
        destination_account: str = "trollie-sim-collection",
        deliveries: int = 1,
    ) -> str:
        """A simulated bank transfer into Trollie's collection account (W1)."""
        event_id = f"evt_{uuid.uuid4().hex}"
        body = json.dumps(
            {
                "id": event_id,
                "type": f"funding.{status}",
                "account": ACCOUNT,
                "environment": self.environment,
                "data": {
                    "transfer_ref": transfer_ref,
                    "reference": reference,
                    "amount_minor": amount_minor,
                    "currency": currency,
                    "destination_account": destination_account,
                },
            }
        )
        with Session(self.engine) as s, s.begin():
            s.add(
                SimWebhook(
                    event_id=event_id,
                    body=body,
                    deliver_after=self.clock.now(),
                    deliveries_remaining=deliveries,
                )
            )
        return event_id

    def open_dispute(self, *, provider_ref: str, amount_minor: int) -> str:
        """The cardholder's bank opens a chargeback against a collected payment (T35)."""
        with Session(self.engine) as s, s.begin():
            p = s.get(SimPayment, provider_ref)
            event_id = f"evt_{uuid.uuid4().hex}"
            body = json.dumps(
                {
                    "id": event_id,
                    "type": "dispute.opened",
                    "account": ACCOUNT,
                    "environment": self.environment,
                    "data": {
                        "provider_ref": provider_ref,
                        "client_key": p.client_key,
                        "status": "disputed",
                        "amount_minor": amount_minor,
                    },
                }
            )
            s.add(SimWebhook(event_id=event_id, body=body, deliver_after=self.clock.now()))
        return event_id

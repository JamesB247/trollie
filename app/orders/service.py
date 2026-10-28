"""Purchase orchestration (blueprint §9). SIMULATED — NOT REAL MONEY.

Each step function is idempotent and driven by persisted state, so it can be re-run after
a crash or a duplicate event. Provider and merchant calls happen outside database
transactions: persist intent -> call -> persist the observed result.

Branch A (card authorise/capture): reserve -> approve -> authorise via hosted checkout ->
revalidate holds -> commit merchants -> one final capture of the accepted total; void
the authorisation if a required leg fails before capture.

Branch B (immediate payment): reserve -> approve -> pay -> revalidate holds (a payment
after hold expiry pauses and re-verifies supply) -> commit -> refund what cannot be
supplied within the approved conditions.
"""

import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.approvals.models import Approval
from app.controls.models import Incident
from app.controls.service import audit, require_not_paused
from app.delivery.models import DeliverySlot
from app.durable import outbox
from app.durable.hashing import canonical_hash
from app.errors import ErrorCode, TrollieError
from app.ledger.postings import courier_owner, post_collection, post_refund_owed
from app.merchants.adapter import MerchantTimeout
from app.merchants.models import Reservation, ReservationState
from app.orders.models import DeliveryJob, Order, OrderLeg
from app.orders.policy import decide
from app.orders.runtime import Runtime
from app.orders.state import DELIVERY, LEG, ORDER, REFUND
from app.payments.models import Action, FinancialOperation, OpState, Refund, RefundState
from app.payments.operations import FINAL, create_operation
from app.payments.profiles import PROFILES, profile_for
from app.quotes.models import Quote, QuoteState
from app.quotes.service import recompute_hash, release_reservations
from app.reconciliation.service import open_case
from app.simulators.courier import CourierTimeout

COLLECT = "collect"


# --- Lookups -------------------------------------------------------------------------


def owned_order(s: Session, order_id: uuid.UUID, account_id: uuid.UUID, *, lock=False) -> Order:
    order = s.get(Order, order_id, with_for_update=lock, populate_existing=lock)
    if order is None or order.account_id != account_id:
        raise TrollieError(ErrorCode.NOT_FOUND, "order not found")
    return order


def _op(s: Session, order_id: uuid.UUID, name: str) -> FinancialOperation | None:
    return s.scalars(
        select(FinancialOperation).where(
            FinancialOperation.idempotency_key == f"order:{order_id}:{name}"
        )
    ).one_or_none()


def _legs(s: Session, order_id: uuid.UUID) -> list[OrderLeg]:
    return list(
        s.scalars(select(OrderLeg).where(OrderLeg.order_id == order_id).order_by(OrderLeg.leg_id))
    )


def _snapshot(s: Session, order: Order) -> dict[str, Any]:
    return s.get(Quote, order.quote_id).snapshot


def _parties(snapshot: dict[str, Any], leg_ids: set[str], *, service_fee: bool) -> list[dict]:
    parties = []
    for leg in snapshot["legs"]:
        if leg["leg_id"] not in leg_ids:
            continue
        parties.append(
            {
                "party_type": "merchant",
                "party_id": leg["seller"]["merchant_id"],
                "beneficiary": f"merchant:{leg['seller']['merchant_id']}",
                "amount_minor": leg["goods_minor"],
                "leg_id": leg["leg_id"],
            }
        )
        courier = str(courier_owner(leg["delivery"]["courier"]))
        parties.append(
            {
                "party_type": "courier",
                "party_id": courier,
                "beneficiary": f"courier:{courier}",
                "amount_minor": leg["delivery"]["fee_minor"],
                "leg_id": leg["leg_id"],
            }
        )
    if service_fee:
        parties.append(
            {
                "party_type": "platform",
                "party_id": None,
                "beneficiary": "platform",
                "amount_minor": snapshot["service_fee_minor"],
                "leg_id": None,
            }
        )
    return parties


def _beneficiaries(parties: list[dict]) -> list[dict]:
    """One entry per provider beneficiary: two legs with the same courier are one payee."""
    gross: dict[str, int] = {}
    for p in parties:
        if p["amount_minor"] > 0:
            gross[p["beneficiary"]] = gross.get(p["beneficiary"], 0) + p["amount_minor"]
    return [{"beneficiary": b, "gross_minor": g} for b, g in sorted(gross.items())]


def _incident(s: Session, kind: str, **details: Any) -> None:
    s.add(Incident(kind=kind, severity="high", details={k: str(v) for k, v in details.items()}))


# --- Create and start ----------------------------------------------------------------


def _authority(s: Session, rt: Runtime, account_id: uuid.UUID, approval_id, mandate_execution_id):
    """Resolve the single authority for this execution: a passkey approval of the quote, or a
    mandate execution recorded by the trusted executor (A2). Returns (quote id, hash, filter)."""
    if (approval_id is None) == (mandate_execution_id is None):
        raise TrollieError(ErrorCode.APPROVAL_INVALID, "exactly one authority is required")
    if approval_id is not None:
        approval = s.get(Approval, approval_id)
        if (
            approval is None
            or approval.account_id != account_id
            or approval.subject_type != ("quote")
        ):
            raise TrollieError(ErrorCode.APPROVAL_INVALID, "approval not found")
        return approval.subject_id, approval.subject_hash, Order.approval_id == approval_id
    from app.wallet.models import MandateExecution

    if not rt.mandate_fixture_enabled:
        raise TrollieError(ErrorCode.CAPABILITY_NOT_ENABLED, "mandate execution is disabled")
    execution = s.get(MandateExecution, mandate_execution_id)
    if execution is None:
        raise TrollieError(ErrorCode.APPROVAL_INVALID, "mandate execution not found")
    return (
        execution.quote_id,
        execution.quote_hash,
        Order.mandate_execution_id == mandate_execution_id,
    )


def create_order(
    rt: Runtime,
    *,
    account_id: uuid.UUID,
    approval_id: uuid.UUID | None = None,
    mandate_execution_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Consume a valid authority and start exactly one execution for it (T18, T24, T31)."""
    try:
        with rt.sessions() as s, s.begin():
            quote_id, approved_hash, same_authority = _authority(
                s, rt, account_id, approval_id, mandate_execution_id
            )
            # Lock the quote first: concurrent requests for this authority queue here, then
            # find the order the first one created (T24).
            quote = s.get(Quote, quote_id, with_for_update=True, populate_existing=True)
            if quote.account_id != account_id:
                raise TrollieError(ErrorCode.APPROVAL_INVALID, "approval not found")
            existing = s.scalars(select(Order).where(same_authority)).first()
            if existing is not None:
                return existing.id  # one logical purchase per authority
            snapshot_hash = recompute_hash(quote)
            if not (approved_hash == quote.quote_hash == snapshot_hash):
                raise TrollieError(
                    ErrorCode.REAPPROVAL_REQUIRED, "approved conditions do not match the quote"
                )  # T18
            if quote.state != QuoteState.APPROVED:
                raise TrollieError(
                    ErrorCode.INVALID_STATE_TRANSITION, "quote is not approved", state=quote.state
                )
            if quote.expires_at <= rt.clock.now():
                quote.state = QuoteState.EXPIRED
                quote.state_version += 1
                raise TrollieError(ErrorCode.QUOTE_EXPIRED, "quote expired; approve a new quote")
            require_not_paused(s, "payments")
            snapshot = quote.snapshot
            wallet_funded = snapshot["funding_source"].startswith("wallet:")
            profile = (
                PROFILES["simwallet"]
                if wallet_funded
                else profile_for(snapshot["funding_source"], rt.profile_override)
            )
            parties = _parties(
                snapshot, {leg["leg_id"] for leg in snapshot["legs"]}, service_fee=True
            )
            beneficiaries = {p["beneficiary"] for p in parties if p["amount_minor"] > 0}
            # T31: the topology must fit the profile before any provider call.
            profile.require("max_additional_beneficiaries", len(beneficiaries) - 1)
            order = Order(
                account_id=account_id,
                quote_id=quote.id,
                approval_id=approval_id,
                mandate_execution_id=mandate_execution_id,
                approved_hash=approved_hash,
                execution_snapshot_hash=snapshot_hash,
                funding_source=snapshot["funding_source"],
                profile_key=profile.key,
                address_version_id=uuid.UUID(snapshot["destination"]["address_version_id"]),
                plan={},
            )
            s.add(order)
            s.flush()
            ORDER.move(order, "PAYMENT_PENDING")
            for leg in snapshot["legs"]:
                s.add(
                    OrderLeg(
                        order_id=order.id,
                        leg_id=leg["leg_id"],
                        merchant_id=uuid.UUID(leg["seller"]["merchant_id"]),
                        location_id=uuid.UUID(leg["location_id"]),
                        reservation_id=uuid.UUID(leg["reservation"]["id"]),
                        commit_ref=f"ord-{order.id}-{leg['leg_id']}",
                        goods_minor=leg["goods_minor"],
                        delivery_minor=leg["delivery"]["fee_minor"],
                        line_ids=[ln["line_id"] for ln in leg["lines"]],
                    )
                )
            if wallet_funded:
                # W16: no external debit at all; funds are held inside the wallet instead.
                from app.wallet.service import reserve

                reserve(
                    s,
                    account_id=account_id,
                    order_id=order.id,
                    funding_source=snapshot["funding_source"],
                    amount_minor=quote.maximum_payable_minor,
                )
            else:
                action = Action.AUTHORISE if profile.collection == "auth_capture" else Action.CHARGE
                create_operation(
                    s,
                    order_id=order.id,
                    action=action,
                    profile=profile,
                    amount_minor=quote.maximum_payable_minor,
                    idempotency_key=f"order:{order.id}:{COLLECT}",
                    request={"quote_hash": quote.quote_hash},
                )
            quote.state = QuoteState.EXECUTING
            quote.state_version += 1
            outbox.emit(
                s,
                aggregate_type="order",
                aggregate_id=order.id,
                aggregate_version=1,
                event_type="order.created",
                payload={"quote_id": str(quote.id)},
            )
            audit(
                s,
                actor=f"account:{account_id}",
                action="order.create",
                object_type="order",
                object_id=order.id,
                approval_id=str(approval_id),
                mandate_execution_id=str(mandate_execution_id),
            )
            return order.id
    except IntegrityError:
        # A concurrent request for the same authority won the unique constraint (T24).
        with rt.sessions() as s:
            column = (
                Order.approval_id == approval_id
                if approval_id
                else Order.mandate_execution_id == mandate_execution_id
            )
            return s.scalars(select(Order.id).where(column)).one()


def start_checkout(rt: Runtime, *, account_id: uuid.UUID, order_id: uuid.UUID) -> str | None:
    """Create the provider-hosted checkout. Returns its reference; no card data passes here."""
    with rt.sessions() as s:
        order = owned_order(s, order_id, account_id)
        op = _op(s, order.id, COLLECT)
        snapshot = _snapshot(s, order)
        profile = PROFILES[order.profile_key]
        parties = _parties(snapshot, {leg["leg_id"] for leg in snapshot["legs"]}, service_fee=True)
    op = rt.executor.submit(
        op.id,
        collection=profile.collection,
        reference=f"order-{order_id}",
        beneficiaries=_beneficiaries(parties),
    )
    if op.state == OpState.UNKNOWN:
        op = rt.executor.reconcile(op.id)
    return op.external_ref


def request_cancellation(rt: Runtime, *, account_id: uuid.UUID, order_id: uuid.UUID) -> str:
    """Record the request; the outcome depends on observed financial state (T39)."""
    with rt.sessions() as s, s.begin():
        order = owned_order(s, order_id, account_id, lock=True)
        order.customer_cancel_requested = True
        audit(
            s,
            actor=f"account:{account_id}",
            action="order.cancel_request",
            object_type="order",
            object_id=order.id,
        )
    advance(rt, order_id)
    return "cancellation_requested"


# --- The driver ----------------------------------------------------------------------


def _lock_key(order_id: uuid.UUID) -> int:
    """Signed 64-bit key for a Postgres advisory lock derived from the order id."""
    return int.from_bytes(order_id.bytes[:8], "big", signed=True)


def advance(rt: Runtime, order_id: uuid.UUID, *, max_steps: int = 20) -> None:
    """Drive one order forward. Only one worker advances a given order at a time: steps are
    idempotent, but two interleaved steps on the same order could act on stale state."""
    with rt.sessions() as lock:
        key = _lock_key(order_id)
        if not lock.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key}).scalar():
            return  # another worker holds it and will observe any new state on its next step
        try:
            _advance_steps(rt, order_id, max_steps)
        finally:
            lock.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
            lock.commit()


def _advance_steps(rt: Runtime, order_id: uuid.UUID, max_steps: int) -> None:
    for _ in range(max_steps):
        with rt.sessions() as s:
            order = s.get(Order, order_id)
            state, wallet_funded = order.state, order.funding_source.startswith("wallet:")
        if wallet_funded:
            from app.wallet.orders import WALLET_STEPS

            step = WALLET_STEPS.get(state)
            if step is None or not step(rt, order_id):
                return
            continue
        step = {
            "PAYMENT_PENDING": _payment_pending,
            "COMMITTING": _committing,
            "COMPENSATING": _compensating,
            "FULFILLING": _fulfilling,
            "NEEDS_ATTENTION": _needs_attention,
            "CANCELLED": _after_cancel,
            "EXPIRED": _after_cancel,
        }.get(state)
        if step is None or not step(rt, order_id):
            return


def _set_state(
    rt: Runtime,
    order_id: uuid.UUID,
    target: str,
    *,
    reason: str | None = None,
    plan: dict | None = None,
) -> None:
    with rt.sessions() as s, s.begin():
        order = s.get(Order, order_id, with_for_update=True)
        ORDER.move(order, target)
        if reason:
            order.attention_reason = reason
        if plan is not None:
            order.plan = plan
        outbox.emit(
            s,
            aggregate_type="order",
            aggregate_id=order.id,
            aggregate_version=order.version,
            event_type=f"order.{target.lower()}",
            payload={"reason": reason},
        )


def _holds_valid(rt: Runtime, order_id: uuid.UUID) -> list[str]:
    """Leg ids whose reservation is not held right now (T08, T09)."""
    bad = []
    with rt.sessions() as s:
        legs = [(leg.leg_id, s.get(Reservation, leg.reservation_id)) for leg in _legs(s, order_id)]
    for leg_id, res in legs:
        if res.state != ReservationState.HELD or res.expires_at <= rt.clock.now():
            bad.append(leg_id)
            continue
        try:
            obs = rt.merchant.get_reservation(client_ref=res.client_ref)
        except MerchantTimeout:
            bad.append(leg_id)
            continue
        if obs.status != "held":
            bad.append(leg_id)
    if bad:
        with rt.sessions() as s, s.begin():
            for leg in _legs(s, order_id):
                if leg.leg_id in bad:
                    res = s.get(Reservation, leg.reservation_id, with_for_update=True)
                    if res.state == ReservationState.HELD:
                        res.state = ReservationState.EXPIRED
                        res.version += 1
    return bad


def _resecure_supply(rt: Runtime, order_id: uuid.UUID, leg_ids: list[str]) -> bool:
    """Branch B only: payment arrived after a hold expired; try to hold the same lines again
    at the same price. Never a different item, price or merchant (T09)."""
    for leg_id in leg_ids:
        with rt.sessions() as s, s.begin():
            leg = s.scalars(
                select(OrderLeg)
                .where(OrderLeg.order_id == order_id, OrderLeg.leg_id == leg_id)
                .with_for_update()
            ).one()
            old = s.get(Reservation, leg.reservation_id)
            new = Reservation(
                location_id=old.location_id,
                merchant_id=old.merchant_id,
                client_ref=f"res-{uuid.uuid4()}",
                lines=old.lines,
                lines_hash=old.lines_hash,
            )
            s.add(new)
            s.flush()
            new_id, client_ref, location_id, lines = (
                new.id,
                new.client_ref,
                new.location_id,
                [dict(ln) for ln in old.lines],
            )
        from app.merchants.adapter import ReservationLine

        try:
            obs = rt.merchant.prepare_reservation(
                location_id=location_id,
                client_ref=client_ref,
                lines=[
                    ReservationLine(
                        uuid.UUID(ln["product_id"]),
                        ln["merchant_sku"],
                        ln["units"],
                        ln["unit_price_minor"],
                    )
                    for ln in lines
                ],
            )
        except MerchantTimeout:
            obs = None
        with rt.sessions() as s, s.begin():
            new = s.get(Reservation, new_id, with_for_update=True)
            if obs is not None and obs.status == "held":
                new.state, new.merchant_ref, new.expires_at = (
                    ReservationState.HELD,
                    obs.merchant_ref,
                    obs.expires_at,
                )
                leg = s.scalars(
                    select(OrderLeg)
                    .where(OrderLeg.order_id == order_id, OrderLeg.leg_id == leg_id)
                    .with_for_update()
                ).one()
                leg.reservation_id = new.id
                leg.evidence = {**leg.evidence, "resecured_reservation": str(new.id)}
            else:
                new.state = ReservationState.REJECTED if obs else ReservationState.UNKNOWN
                return False
    return True


def _payment_pending(rt: Runtime, order_id: uuid.UUID) -> bool:
    with rt.sessions() as s:
        order = s.get(Order, order_id)
        op = _op(s, order_id, COLLECT)
        cancel = order.customer_cancel_requested
    if op.state in (OpState.UNKNOWN, OpState.RECONCILING):
        return rt.executor.reconcile(op.id).state != op.state
    if op.state in (OpState.CREATED, OpState.SUBMITTED, OpState.PENDING):
        if cancel and op.state == OpState.CREATED:
            _release_all(rt, order_id)
            _set_state(rt, order_id, "CANCELLED", reason="cancelled_before_payment")
            return True
        return False  # waiting for the customer; a live payment attempt is never abandoned
    if op.state == OpState.FAILED_FINAL:
        _release_all(rt, order_id)
        _invalidate_quote(rt, order_id)
        _set_state(rt, order_id, "CANCELLED", reason="payment_failed")
        return True
    # SUCCEEDED: confirm authoritatively before acting on the evidence (T30).
    confirmed = rt.executor.confirm(op.id)
    if confirmed is None:
        return False
    from app.payments.operations import target_state

    if target_state(op.action, confirmed.status) != OpState.SUCCEEDED:
        with rt.sessions() as s, s.begin():
            open_case(
                s,
                dedupe_key=f"confirm:{op.id}",
                case_type="callback_lookup_conflict",
                refs={"operation_id": str(op.id), "lookup": confirmed.status},
                difference_minor=op.amount_minor,
            )
        _set_state(rt, order_id, "NEEDS_ATTENTION", reason="payment_evidence_conflict")
        return True
    if cancel:
        _set_state(
            rt,
            order_id,
            "COMPENSATING",
            reason="customer_cancelled",
            plan={"kind": "cancel_all", "reason": "customer_cancelled"},
        )
        return True
    expired = _holds_valid(rt, order_id)
    if not expired:
        _set_state(rt, order_id, "COMMITTING")
        return True
    if op.action == Action.AUTHORISE:
        _set_state(
            rt,
            order_id,
            "COMPENSATING",
            reason="reservation_expired",
            plan={"kind": "cancel_all", "reason": "reservation_expired_reapproval_required"},
        )
        return True
    _set_state(rt, order_id, "NEEDS_ATTENTION", reason="payment_after_hold_expiry")
    if _resecure_supply(rt, order_id, expired):
        _set_state(rt, order_id, "COMMITTING", reason="supply_resecured")
    else:
        _set_state(
            rt,
            order_id,
            "COMPENSATING",
            reason="supply_not_secured",
            plan={"kind": "cancel_all", "reason": "supply_not_secured"},
        )
    return True


def _needs_attention(rt: Runtime, order_id: uuid.UUID) -> bool:
    return False  # a person resolves it with evidence; no automatic dispatch


def _commit_leg(rt: Runtime, leg_id: uuid.UUID) -> None:
    with rt.sessions() as s, s.begin():
        leg = s.get(OrderLeg, leg_id, with_for_update=True)
        if leg.state == "RESERVED":
            LEG.move(leg, "COMMIT_REQUESTED")
        elif leg.state not in ("COMMIT_REQUESTED", "UNKNOWN"):
            return
        res = s.get(Reservation, leg.reservation_id)
        args = {
            "location_id": leg.location_id,
            "client_ref": leg.commit_ref,
            "reservation_ref": res.merchant_ref,
        }
        state = leg.state
    try:
        if state == "UNKNOWN":
            obs = rt.merchant.get_order(client_ref=args["client_ref"])
            if obs.status == "not_found":
                obs = rt.merchant.commit_order(**args)  # never acted: same reference, safe
        else:
            obs = rt.merchant.commit_order(**args)
    except MerchantTimeout:
        try:
            obs = rt.merchant.get_order(client_ref=args["client_ref"])
        except MerchantTimeout:
            obs = None
        if obs is not None and obs.status == "not_found":
            obs = None
    with rt.sessions() as s, s.begin():
        leg = s.get(OrderLeg, leg_id, with_for_update=True)
        res = s.get(Reservation, leg.reservation_id, with_for_update=True)
        if obs is None:
            if leg.state == "COMMIT_REQUESTED":
                LEG.move(leg, "UNKNOWN")
            return
        leg.merchant_ref = obs.merchant_ref
        leg.evidence = {**leg.evidence, "commit": obs.status, "reason": obs.reason}
        if obs.status in ("accepted", "ready"):
            LEG.move(leg, "ACCEPTED")
            res.state = ReservationState.CONSUMED
        else:
            LEG.move(leg, "REJECTED")
            if obs.reason == "stock_lost":  # T10: a held reservation proved false
                _incident(
                    s, "merchant_reservation_unreliable", leg_id=leg.id, location_id=leg.location_id
                )
        res.version += 1


def resolve_uncertain_leg(rt: Runtime, leg_id: uuid.UUID) -> str | None:
    """Before cancelling, establish what the merchant actually has for an uncertain leg.
    Returns the leg's resolved state, or None while the merchant cannot be reached."""
    with rt.sessions() as s:
        leg = s.get(OrderLeg, leg_id)
        if leg.state not in ("COMMIT_REQUESTED", "UNKNOWN"):
            return leg.state
        ref = leg.commit_ref
    try:
        obs = rt.merchant.get_order(client_ref=ref)
    except MerchantTimeout:
        return None
    with rt.sessions() as s, s.begin():
        leg = s.get(OrderLeg, leg_id, with_for_update=True)
        if leg.state == "COMMIT_REQUESTED":
            LEG.move(leg, "UNKNOWN")
        if obs.status in ("accepted", "ready"):
            LEG.move(leg, "ACCEPTED")
            leg.merchant_ref = obs.merchant_ref
        else:  # rejected, or never received: no commitment exists under this reference
            LEG.move(leg, "REJECTED")
            leg.evidence = {**leg.evidence, "resolved_for_cancellation": obs.status}
        return leg.state


def _committing(rt: Runtime, order_id: uuid.UUID) -> bool:
    with rt.sessions() as s:
        pending = [
            leg.id
            for leg in _legs(s, order_id)
            if leg.state in ("RESERVED", "COMMIT_REQUESTED", "UNKNOWN")
        ]
    for leg_id in pending:
        _commit_leg(rt, leg_id)
    with rt.sessions() as s:
        order = s.get(Order, order_id)
        legs = _legs(s, order_id)
        if any(leg.state in ("COMMIT_REQUESTED", "UNKNOWN") for leg in legs):
            return False  # unresolved merchant state: reconcile by lookup, never re-order
        snapshot = _snapshot(s, order)
        rejected = {leg.leg_id for leg in legs if leg.state == "REJECTED"}
        collect = _op(s, order_id, COLLECT)
        decision = decide(snapshot, rejected)
    if decision.kind == "cancel_all":
        _set_state(
            rt,
            order_id,
            "COMPENSATING",
            reason=decision.reason,
            plan={"kind": "cancel_all", "reason": decision.reason},
        )
        return True
    keep = {leg["leg_id"] for leg in snapshot["legs"]} - set(decision.removed_leg_ids)
    parties = _parties(snapshot, keep, service_fee=True)
    accepted_total = sum(p["amount_minor"] for p in parties)
    plan = {
        "kind": decision.kind,
        "reason": decision.reason,
        "removed_leg_ids": list(decision.removed_leg_ids),
    }
    if collect.action == Action.AUTHORISE:
        if accepted_total > collect.amount_minor:  # captured <= customer authority (§7.3)
            raise TrollieError(ErrorCode.AUTHORITY_DENIED, "capture would exceed authority")
        profile = PROFILES[collect.profile_key]
        if decision.kind == "partial" and profile.allocation_fixed_at != "capture":
            # The provider would settle the removed leg's share anyway: fail closed.
            _set_state(
                rt,
                order_id,
                "COMPENSATING",
                reason="partial_capture_not_supported",
                plan={"kind": "cancel_all", "reason": "partial_capture_not_supported"},
            )
            return True
        with rt.sessions() as s, s.begin():
            capture = create_operation(
                s,
                order_id=order_id,
                action=Action.CAPTURE,
                profile=PROFILES[collect.profile_key],
                amount_minor=accepted_total,
                idempotency_key=f"order:{order_id}:capture",
                request={"plan": plan},
                parent_id=collect.id,
            )
            s.get(Order, order_id, with_for_update=True).plan = plan
        capture = rt.executor.submit(capture.id, beneficiaries=_beneficiaries(parties))
        if capture.state in (OpState.UNKNOWN, OpState.SUBMITTED):
            capture = rt.executor.reconcile(capture.id)
        if capture.state == OpState.FAILED_FINAL:
            # Do not dispatch unpaid goods: cancel the committed merchant orders.
            _set_state(
                rt,
                order_id,
                "COMPENSATING",
                reason="capture_failed",
                plan={"kind": "cancel_all", "reason": "capture_failed"},
            )
            return True
        if capture.state != OpState.SUCCEEDED:
            return False
        with rt.sessions() as s, s.begin():
            post_collection(
                s, operation_id=capture.id, amount_minor=capture.amount_minor, parties=parties
            )
            cancel = s.get(Order, order_id).customer_cancel_requested
        if cancel:  # T39: cancellation raced the capture; the observed capture decides
            _set_state(
                rt,
                order_id,
                "COMPENSATING",
                reason="customer_cancelled",
                plan={**plan, "kind": "cancel_all", "reason": "customer_cancelled"},
            )
            return True
    else:
        with rt.sessions() as s, s.begin():
            all_parties = _parties(
                snapshot, {leg["leg_id"] for leg in snapshot["legs"]}, service_fee=True
            )
            post_collection(
                s, operation_id=collect.id, amount_minor=collect.amount_minor, parties=all_parties
            )
            s.get(Order, order_id, with_for_update=True).plan = plan
        if decision.removed_leg_ids:
            removed = [
                p
                for p in _parties(snapshot, set(decision.removed_leg_ids), service_fee=False)
                if p["amount_minor"] > 0
            ]
            create_refund(
                rt,
                order_id=order_id,
                business_key=f"order:{order_id}:partial",
                parties=removed,
                reason="permitted_omission",
            )
    _book_deliveries(rt, order_id, keep)
    _set_state(rt, order_id, "FULFILLING", reason=decision.reason if rejected else None)
    return True


def _release_all(rt: Runtime, order_id: uuid.UUID) -> None:
    with rt.sessions() as s:
        ids = [leg.reservation_id for leg in _legs(s, order_id)]
    release_reservations(rt.sessions, rt.merchant, ids)


def _invalidate_quote(rt: Runtime, order_id: uuid.UUID) -> None:
    with rt.sessions() as s, s.begin():
        quote = s.get(Quote, s.get(Order, order_id).quote_id, with_for_update=True)
        if quote.state == QuoteState.EXECUTING:
            quote.state = QuoteState.INVALIDATED
            quote.state_version += 1


def _compensating(rt: Runtime, order_id: uuid.UUID) -> bool:
    """cancel_all: stop every leg, then void the hold or refund what was collected."""
    with rt.sessions() as s:
        uncertain = [
            leg.id for leg in _legs(s, order_id) if leg.state in ("COMMIT_REQUESTED", "UNKNOWN")
        ]
    if any(resolve_uncertain_leg(rt, leg_id) is None for leg_id in uncertain):
        return False  # not safe to release or refund until the merchant state is known
    with rt.sessions() as s:
        legs = [(leg.id, leg.state, leg.commit_ref) for leg in _legs(s, order_id)]
    for leg_id, state, commit_ref in legs:
        if state in ("ACCEPTED", "PICKING", "READY_FOR_COLLECTION"):
            with rt.sessions() as s, s.begin():
                LEG.move(s.get(OrderLeg, leg_id, with_for_update=True), "CANCEL_REQUESTED")
            try:
                obs = rt.merchant.cancel_order(client_ref=commit_ref)
            except MerchantTimeout:
                continue
            with rt.sessions() as s, s.begin():
                leg = s.get(OrderLeg, leg_id, with_for_update=True)
                LEG.move(leg, "CANCELLED" if obs.status == "cancelled" else "ACCEPTED")
        elif state == "RESERVED":
            with rt.sessions() as s, s.begin():
                LEG.move(s.get(OrderLeg, leg_id, with_for_update=True), "CANCELLED")
    _release_all(rt, order_id)

    with rt.sessions() as s:
        collect = _op(s, order_id, COLLECT)
        capture = _op(s, order_id, "capture")
        order = s.get(Order, order_id)
        snapshot = _snapshot(s, order)
    if collect.state in (OpState.UNKNOWN, OpState.RECONCILING, OpState.SUBMITTED, OpState.PENDING):
        rt.executor.reconcile(collect.id)
        return False
    money_done = True
    if collect.state == OpState.SUCCEEDED:
        if collect.action == Action.AUTHORISE and (
            capture is None or capture.state == OpState.FAILED_FINAL
        ):
            with rt.sessions() as s, s.begin():
                void = create_operation(
                    s,
                    order_id=order_id,
                    action=Action.VOID,
                    profile=PROFILES[collect.profile_key],
                    amount_minor=collect.amount_minor,
                    idempotency_key=f"order:{order_id}:void",
                    request={},
                    parent_id=collect.id,
                )
            void = rt.executor.submit(void.id)
            if void.state not in FINAL:
                void = rt.executor.reconcile(void.id)
            money_done = void.state in FINAL
        elif capture is not None and capture.state in (OpState.UNKNOWN, OpState.SUBMITTED):
            rt.executor.reconcile(capture.id)  # T39: observe the capture before deciding
            return False
        else:
            paid = capture if capture is not None else collect
            if paid.state == OpState.SUCCEEDED:
                legs_paid = {leg["leg_id"] for leg in snapshot["legs"]} - set(
                    order.plan.get("removed_leg_ids", [])
                )
                parties = [
                    p
                    for p in _parties(snapshot, legs_paid, service_fee=True)
                    if p["amount_minor"] > 0
                ]
                if collect.action == Action.CHARGE and not _posted_collection(rt, collect.id):
                    with rt.sessions() as s, s.begin():
                        post_collection(
                            s,
                            operation_id=collect.id,
                            amount_minor=collect.amount_minor,
                            parties=_parties(snapshot, legs_paid, service_fee=True),
                        )
                elif collect.action == Action.AUTHORISE and not _posted_collection(rt, paid.id):
                    with rt.sessions() as s, s.begin():
                        post_collection(
                            s, operation_id=paid.id, amount_minor=paid.amount_minor, parties=parties
                        )
                create_refund(
                    rt,
                    order_id=order_id,
                    business_key=f"order:{order_id}:cancel_all",
                    parties=parties,
                    reason=order.plan.get("reason", "cancelled"),
                )
    if not money_done:
        return False
    _invalidate_quote(rt, order_id)
    _set_state(rt, order_id, "CANCELLED")
    return True


def _posted_collection(rt: Runtime, op_id: uuid.UUID) -> bool:
    from app.ledger.models import LedgerTransaction

    with rt.sessions() as s:
        return (
            s.scalars(
                select(LedgerTransaction.id).where(
                    LedgerTransaction.posting_key == f"collection:{op_id}"
                )
            ).first()
            is not None
        )


def _after_cancel(rt: Runtime, order_id: uuid.UUID) -> bool:
    """A late successful debit after cancellation creates a refund obligation (§8.5)."""
    with rt.sessions() as s:
        collect = _op(s, order_id, COLLECT)
        void = _op(s, order_id, "void")
        refunds = s.scalars(select(Refund.id).where(Refund.order_id == order_id)).all()
    if collect.state != OpState.SUCCEEDED or void is not None or refunds:
        return False
    with rt.sessions() as s, s.begin():
        _incident(s, "late_payment_after_cancellation", order_id=order_id, op=collect.id)
    _set_state(
        rt,
        order_id,
        "COMPENSATING",
        reason="late_payment",
        plan={"kind": "cancel_all", "reason": "late_payment_after_cancellation"},
    )
    return True


# --- Refunds -------------------------------------------------------------------------


def create_refund(
    rt: Runtime, *, order_id: uuid.UUID, business_key: str, parties: list[dict], reason: str
) -> uuid.UUID:
    """One refund per business key; total refunds never exceed what was collected (T33/T34)."""
    amount = sum(p["amount_minor"] for p in parties)
    _hold_if_disputed(rt, order_id, business_key, amount)
    with rt.sessions() as s, s.begin():
        existing = s.scalars(select(Refund).where(Refund.business_key == business_key)).first()
        if existing is not None:
            if existing.amount_minor != amount:
                raise TrollieError(
                    ErrorCode.DUPLICATE_OPERATION_CONFLICT,
                    "refund key reused with a different amount",
                )
            refund_id = existing.id
        else:
            order = s.get(Order, order_id, with_for_update=True)  # serialises refund caps
            paid = _op(s, order_id, "capture") or _op(s, order_id, COLLECT)
            if paid.state != OpState.SUCCEEDED:
                raise TrollieError(ErrorCode.INVALID_STATE_TRANSITION, "nothing collected")
            committed = sum(
                r.amount_minor
                for r in s.scalars(
                    select(Refund).where(
                        Refund.order_id == order_id,
                        Refund.state.not_in([RefundState.REJECTED_WITH_REASON]),
                    )
                )
            )
            if committed + amount > paid.amount_minor:
                raise TrollieError(
                    ErrorCode.VALIDATION_FAILED,
                    "refund exceeds the remaining refundable amount",
                    refundable=paid.amount_minor - committed,
                )
            refund = Refund(
                order_id=order_id,
                business_key=business_key,
                original_operation_id=paid.id,
                reason=reason,
                amount_minor=amount,
                economic_allocation=[
                    {k: p[k] for k in ("party_type", "party_id", "amount_minor", "leg_id")}
                    for p in parties
                ],
                destination="original_payment",
            )
            s.add(refund)
            s.flush()
            REFUND.move(refund, RefundState.ASSESSED)
            REFUND.move(refund, RefundState.APPROVED)
            post_refund_owed(s, refund_id=refund.id, account_id=order.account_id, parties=parties)
            op = create_operation(
                s,
                order_id=order_id,
                action=Action.REFUND,
                profile=PROFILES[paid.profile_key],
                amount_minor=amount,
                idempotency_key=f"refund:{refund.id}",
                request={"business_key": business_key},
                parent_id=paid.id,
            )
            refund.operation_id = op.id
            refund_id = refund.id
    submit_refund(rt, refund_id)
    return refund_id


def _hold_if_disputed(rt: Runtime, order_id: uuid.UUID, business_key: str, amount: int) -> None:
    """T35: while a chargeback is open the customer may already be reimbursed through it.
    Record the overlap (committed on its own) and hold the refund for finance."""
    from app.reconciliation.models import ReconciliationCase

    with rt.sessions() as s, s.begin():
        if s.scalars(select(Refund.id).where(Refund.business_key == business_key)).first():
            return  # an existing refund is replayed, not re-decided
        paid = _op(s, order_id, "capture") or _op(s, order_id, COLLECT)
        if (
            paid is None
            or not s.scalars(
                select(ReconciliationCase.id).where(
                    ReconciliationCase.dedupe_key == f"dispute:{paid.id}",
                    ReconciliationCase.state == "open",
                )
            ).first()
        ):
            return
        open_case(
            s,
            dedupe_key=f"dispute-overlap:{paid.id}",
            case_type="dispute_refund_overlap",
            refs={"operation_id": str(paid.id), "requested_refund": business_key},
            difference_minor=amount,
        )
    raise TrollieError(
        ErrorCode.REFUND_HELD_DISPUTE_OPEN,
        "refund held while a chargeback is open; finance will resolve",
    )


def submit_refund(rt: Runtime, refund_id: uuid.UUID) -> None:
    from app.payments.refunds import sync_refund

    with rt.sessions() as s:
        op_id = s.get(Refund, refund_id).operation_id
    op = rt.executor.submit(op_id)
    if op.state == OpState.UNKNOWN:
        rt.executor.reconcile(op_id)
    sync_refund(rt, refund_id)


# --- Delivery ------------------------------------------------------------------------


def _book_deliveries(rt: Runtime, order_id: uuid.UUID, leg_ids: set[str]) -> None:
    with rt.sessions() as s, s.begin():
        order = s.get(Order, order_id)
        snapshot = _snapshot(s, order)
        slots = {leg["leg_id"]: leg["delivery"] for leg in snapshot["legs"]}
        for leg in _legs(s, order_id):
            if (
                leg.leg_id not in leg_ids
                or s.scalars(select(DeliveryJob).where(DeliveryJob.order_leg_id == leg.id)).first()
            ):
                continue
            slot = s.get(
                DeliverySlot, uuid.UUID(slots[leg.leg_id]["slot_id"]), with_for_update=True
            )
            slot.booked += 1
            s.add(
                DeliveryJob(
                    order_leg_id=leg.id,
                    slot_id=slot.id,
                    courier_code=slots[leg.leg_id]["courier"],
                    booking_ref=f"book-{leg.id}",
                    address_version_id=order.address_version_id,
                )
            )
    with rt.sessions() as s:
        jobs = [
            j.id
            for j in s.scalars(
                select(DeliveryJob)
                .join(OrderLeg, OrderLeg.id == DeliveryJob.order_leg_id)
                .where(OrderLeg.order_id == order_id)
            )
        ]
    for job_id in jobs:
        book_delivery(rt, job_id)


def book_delivery(rt: Runtime, job_id: uuid.UUID) -> str:
    with rt.sessions() as s, s.begin():
        job = s.get(DeliveryJob, job_id, with_for_update=True)
        if job.state == "QUOTED":
            DELIVERY.move(job, "BOOK_REQUESTED")
        elif job.state not in ("BOOK_REQUESTED", "BOOKING_UNKNOWN"):
            return job.state
        leg = s.get(OrderLeg, job.order_leg_id)
        args = {
            "booking_ref": job.booking_ref,
            "slot_id": job.slot_id,
            "location_id": leg.location_id,
            "address_version_id": job.address_version_id,
        }
    try:
        obs = rt.courier.book(**args)
    except CourierTimeout:
        try:
            obs = rt.courier.get_booking(booking_ref=args["booking_ref"])  # T40: look up first
        except CourierTimeout:
            obs = None
        if obs is not None and obs["status"] == "not_found":
            obs = None
    with rt.sessions() as s, s.begin():
        job = s.get(DeliveryJob, job_id, with_for_update=True)
        if obs is None:
            if job.state == "BOOK_REQUESTED":
                DELIVERY.move(job, "BOOKING_UNKNOWN")
        elif obs["status"] == "booked":
            DELIVERY.move(job, "BOOKED")
            job.courier_ref = obs["courier_ref"]
        else:
            DELIVERY.move(job, "FAILED")
        return job.state


def redirect_delivery(
    rt: Runtime, *, job_id: uuid.UUID, address_version_id: uuid.UUID, requested_by: str
) -> None:
    """A driver or merchant cannot change the approved destination (T42)."""
    with rt.sessions() as s, s.begin():
        job = s.get(DeliveryJob, job_id)
        audit(
            s,
            actor=requested_by,
            action="delivery.redirect_rejected",
            object_type="delivery_job",
            object_id=job_id,
            result="rejected",
            requested_address=str(address_version_id),
        )
    raise TrollieError(
        ErrorCode.REAPPROVAL_REQUIRED,
        "delivery address differs from the approved destination",
        approved=str(job.address_version_id),
    )


def merchant_ready(rt: Runtime, *, leg_id: uuid.UUID) -> None:
    with rt.sessions() as s:
        ref = s.get(OrderLeg, leg_id).commit_ref
    obs = rt.merchant.mark_ready(client_ref=ref)
    with rt.sessions() as s, s.begin():
        leg = s.get(OrderLeg, leg_id, with_for_update=True)
        if obs.status == "ready":
            LEG.move(leg, "READY_FOR_COLLECTION")


def courier_progress(rt: Runtime, *, job_id: uuid.UUID, to: str) -> None:
    """Driver-side updates: collected | delivered | failed."""
    with rt.sessions() as s:
        job = s.get(DeliveryJob, job_id)
        ref = job.booking_ref
    rt.courier.advance(booking_ref=ref, to=to)
    with rt.sessions() as s, s.begin():
        job = s.get(DeliveryJob, job_id, with_for_update=True)
        leg = s.get(OrderLeg, job.order_leg_id, with_for_update=True)
        if to == "collected":
            DELIVERY.move(job, "COLLECTING")
            LEG.move(leg, "COLLECTED")
        elif to == "delivered":
            if job.state == "COLLECTING":
                DELIVERY.move(job, "IN_TRANSIT")
            DELIVERY.move(job, "DELIVERED")
            LEG.move(leg, "DELIVERED")
        else:
            DELIVERY.move(job, "FAILED")
            LEG.move(leg, "FAILED")
            _incident(s, "delivery_failed", job_id=job.id)
        order_id = leg.order_id
    advance(rt, order_id)


def _fulfilling(rt: Runtime, order_id: uuid.UUID) -> bool:
    with rt.sessions() as s:
        order = s.get(Order, order_id)
        removed = set(order.plan.get("removed_leg_ids", []))
        live = [leg for leg in _legs(s, order_id) if leg.leg_id not in removed]
        # TODO(blueprint §9.5): a cancellation requested after capture but before collection
        # should cancel merchant orders and refund; for now it is handled by support.
        if live and all(leg.state == "DELIVERED" for leg in live):
            target = "PARTIAL" if removed else "COMPLETED"
        else:
            return False
    # PARTIAL is terminal: an expressly permitted partial outcome is reported separately
    # from whole-basket fulfilment (blueprint §19.1).
    _set_state(rt, order_id, target)
    return True


def execution_hash(s: Session, order_id: uuid.UUID) -> str:
    order = s.get(Order, order_id)
    return canonical_hash(s.get(Quote, order.quote_id).snapshot)

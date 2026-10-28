"""Shopping sessions, estimates and firm quotes (blueprint §5, §9.1 steps 1-4).

Estimates come straight from the optimiser and are never purchasable. A firm quote is
derived from an estimate only when every leg holds a merchant reservation for exactly
the estimated lines. Snapshots are immutable and canonically hashed, and expire before
their earliest dependency minus an execution safety margin (§5.5).
"""

import copy
import json
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.accounts.models import AddressVersion
from app.accounts.service import owned_address, verified_programmes
from app.clock import Clock
from app.controls.service import audit
from app.delivery.models import DeliverySlot
from app.durable import outbox
from app.durable.hashing import canonical_hash, canonical_json, sha256_hex
from app.errors import ErrorCode, TrollieError
from app.merchants.adapter import MerchantAdapter, MerchantTimeout, ReservationLine
from app.merchants.models import Merchant, Reservation, ReservationState
from app.offers.models import OfferVersion
from app.products.models import Product
from app.quotes.inputs import build_problem
from app.quotes.models import (
    FulfilmentMode,
    Quote,
    QuoteKind,
    QuoteLeg,
    QuoteState,
    RequestedItem,
    ShoppingSession,
)
from app.quotes.optimiser import (
    POLICY_VERSION,
    Blocking,
    Candidate,
    LineRequest,
    Option,
    Quantity,
    Rule,
    Strategy,
    optimise,
)

SCHEMA = "trollie.quote.v1"
TERMS_VERSION = "pilot-terms-1"
APPROVAL_POLICY_VERSION = "pilot-authority-1"
EXECUTION_SAFETY_MARGIN = timedelta(minutes=2)
PAY_PER_ORDER_SOURCES = ("pay_per_order:card_auth_capture", "pay_per_order:immediate")

# Funding-source validators registered by other modules (the wallet adds its own, A4).
FundingValidator = Callable[[Session, uuid.UUID, str, int], None]
FUNDING_VALIDATORS: dict[str, FundingValidator] = {}


# --- Sessions and items --------------------------------------------------------------


def owned_session(
    session: Session, session_id: uuid.UUID, account_id: uuid.UUID
) -> ShoppingSession:
    row = session.get(ShoppingSession, session_id)
    if row is None or row.account_id != account_id:
        raise TrollieError(ErrorCode.NOT_FOUND, "shopping session not found")
    return row


def owned_quote(
    session: Session, quote_id: uuid.UUID, account_id: uuid.UUID, *, lock: bool = False
) -> Quote:
    quote = session.get(Quote, quote_id, with_for_update=lock, populate_existing=lock)
    if quote is None or quote.account_id != account_id:
        raise TrollieError(ErrorCode.NOT_FOUND, "quote not found")
    return quote


def create_session(
    session: Session,
    *,
    account_id: uuid.UUID,
    address_version_id: uuid.UUID,
    budget_minor: int | None = None,
    deadline: datetime | None = None,
) -> ShoppingSession:
    owned_address(session, account_id, address_version_id)
    row = ShoppingSession(
        account_id=account_id,
        address_version_id=address_version_id,
        budget_minor=budget_minor,
        deadline=deadline,
    )
    session.add(row)
    session.flush()
    return row


def add_item(
    session: Session,
    *,
    session_id: uuid.UUID,
    account_id: uuid.UUID,
    line_id: str,
    rule: Rule,
    candidates: list[Candidate],
    quantity: Quantity,
    must_have: bool = False,
    source: str,
    needs_clarification: str | None = None,
) -> RequestedItem:
    """Record a structured request. References must resolve to existing products; no price,
    payee, address or URL can be supplied through this path."""
    owned_session(session, session_id, account_id)
    if not candidates:
        raise TrollieError(ErrorCode.VALIDATION_FAILED, "at least one candidate product required")
    ids = {c.product_id for c in candidates}
    found = set(session.scalars(select(Product.id).where(Product.id.in_(ids))))
    if found != ids:
        raise TrollieError(
            ErrorCode.VALIDATION_FAILED,
            "unknown product reference",
            unknown=sorted(str(i) for i in ids - found),
        )
    item = RequestedItem(
        session_id=session_id,
        line_id=line_id,
        rule=rule,
        candidates=[
            {
                "product_id": str(c.product_id),
                "rank": c.rank,
                "max_unit_price_minor": c.max_unit_price_minor,
            }
            for c in candidates
        ],
        quantity_packs=quantity.packs,
        quantity_measure=quantity.measure,
        quantity_unit=quantity.unit,
        must_have=must_have,
        source=source,
        needs_clarification=needs_clarification,
    )
    session.add(item)
    session.flush()
    return item


def _line_requests(items: list[RequestedItem]) -> list[LineRequest]:
    return [
        LineRequest(
            line_id=i.line_id,
            rule=Rule(i.rule),
            candidates=tuple(
                Candidate(uuid.UUID(c["product_id"]), c["rank"], c["max_unit_price_minor"])
                for c in i.candidates
            ),
            quantity=Quantity(
                packs=i.quantity_packs, measure=i.quantity_measure, unit=i.quantity_unit
            ),
            must_have=i.must_have,
        )
        for i in sorted(items, key=lambda i: i.line_id)
    ]


# --- Snapshots -----------------------------------------------------------------------


def _jsonable(value: Any) -> Any:
    """The stored snapshot is exactly the canonical JSON form that was hashed."""
    return json.loads(canonical_json(value))


def recompute_hash(quote: Quote) -> str:
    return canonical_hash(quote.snapshot)


def _next_version(session: Session, session_id: uuid.UUID) -> int:
    session.get(ShoppingSession, session_id, with_for_update=True)
    current = session.scalar(select(func.max(Quote.version)).where(Quote.session_id == session_id))
    return (current or 0) + 1


def _destination(address: AddressVersion) -> dict[str, Any]:
    return {
        "address_version_id": address.id,
        "label": address.label,
        "version": address.version,
        "service_zone": address.service_zone,
        "content_sha256": sha256_hex(address.nonce + address.ciphertext),
    }


def _snapshot_legs(session: Session, option: Option, must_have: set[str]) -> list[dict[str, Any]]:
    legs = []
    for n, leg in enumerate(option.legs, start=1):
        merchant = session.get(Merchant, leg.merchant_id)
        slot = session.get(DeliverySlot, leg.slot_id)
        lines = []
        for ln in leg.lines:
            product = session.get(Product, ln.product_id)
            offer = session.get(OfferVersion, ln.offer_version_id)
            lines.append(
                {
                    "line_id": ln.line_id,
                    "product": {
                        "id": product.id,
                        "gtin": product.gtin,
                        "brand": product.brand,
                        "name": product.name,
                        "variant": product.variant,
                        "unit_measure": product.unit_measure,
                        "unit": product.unit,
                        "pack_count": product.pack_count,
                    },
                    "offer_version_id": ln.offer_version_id,
                    "merchant_sku": offer.merchant_sku,
                    "tax_code": offer.tax_code,
                    "units": ln.units,
                    "unit_price_minor": ln.unit_price_minor,
                    "discount_minor": ln.discount_minor,
                    "line_total_minor": ln.line_total_minor,
                    "promotion_id": ln.promotion_id,
                    "must_have": ln.line_id in must_have,
                }
            )
        legs.append(
            {
                "leg_id": f"leg_{n}",
                "seller": {
                    "merchant_id": merchant.id,
                    "legal_name": merchant.legal_name,
                    "display_name": merchant.display_name,
                },
                "location_id": leg.location_id,
                "reservation": None,
                "lines": lines,
                "goods_minor": leg.goods_minor,
                "delivery": {
                    "slot_id": slot.id,
                    "courier": slot.courier_code,
                    "window_start": leg.window_start,
                    "window_end": leg.window_end,
                    "fee_minor": leg.delivery_fee_minor,
                    "promotion_id": leg.delivery_promotion_id,
                },
            }
        )
    return legs


def _dependency_expiry(
    session: Session, snapshot: dict[str, Any], reservations: list[Reservation]
) -> datetime:
    """latest_start_time = earliest relevant expiry - execution safety margin (§5.5)."""
    offer_ids = [ln["offer_version_id"] for leg in snapshot["legs"] for ln in leg["lines"]]
    deadlines = list(
        session.scalars(select(OfferVersion.valid_until).where(OfferVersion.id.in_(offer_ids)))
    )
    deadlines += [
        datetime.fromisoformat(leg["delivery"]["window_start"]) for leg in snapshot["legs"]
    ]
    deadlines += [r.expires_at for r in reservations if r.expires_at]
    return min(deadlines) - EXECUTION_SAFETY_MARGIN


def _store_quote(
    session: Session,
    *,
    shopping: ShoppingSession,
    snapshot: dict[str, Any],
    derived_from: uuid.UUID | None,
) -> Quote:
    stored = _jsonable(snapshot)
    quote = Quote(
        id=uuid.UUID(stored["quote_id"]),
        session_id=shopping.id,
        account_id=shopping.account_id,
        version=stored["version"],
        kind=stored["kind"],
        strategy=stored["strategy"],
        derived_from_id=derived_from,
        snapshot=stored,
        quote_hash=canonical_hash(stored),
        total_minor=stored["total_minor"],
        maximum_payable_minor=stored["maximum_payable_minor"],
        expires_at=datetime.fromisoformat(stored["expires_at"]),
        state=QuoteState.FIRM if stored["kind"] == QuoteKind.FIRM else QuoteState.ESTIMATE,
    )
    session.add(quote)
    session.flush()
    for leg in stored["legs"]:
        session.add(
            QuoteLeg(
                quote_id=quote.id,
                leg_id=leg["leg_id"],
                merchant_id=uuid.UUID(leg["seller"]["merchant_id"]),
                location_id=uuid.UUID(leg["location_id"]),
                reservation_id=uuid.UUID(leg["reservation"]["id"]) if leg["reservation"] else None,
                slot_id=uuid.UUID(leg["delivery"]["slot_id"]),
                goods_minor=leg["goods_minor"],
                delivery_minor=leg["delivery"]["fee_minor"],
            )
        )
    outbox.emit(
        session,
        aggregate_type="quote",
        aggregate_id=quote.id,
        aggregate_version=1,
        event_type=f"quote.{stored['kind']}_created",
        payload={"quote_id": str(quote.id), "quote_hash": quote.quote_hash},
    )
    session.flush()
    return quote


# --- Estimates -----------------------------------------------------------------------


@dataclass
class EstimateResult:
    quotes: dict[Strategy, Quote | None]
    blocking: list[Blocking] = field(default_factory=list)
    omitted_line_ids: tuple[str, ...] = ()


def request_estimates(
    session: Session,
    *,
    session_id: uuid.UUID,
    account_id: uuid.UUID,
    clock: Clock,
    allow_omit_optional: bool = False,
) -> EstimateResult:
    shopping = owned_session(session, session_id, account_id)
    items = list(
        session.scalars(select(RequestedItem).where(RequestedItem.session_id == shopping.id))
    )
    unclear = [i.line_id for i in items if i.needs_clarification]
    if unclear:  # T02/T03/T59: never quote an ambiguous request
        raise TrollieError(
            ErrorCode.VALIDATION_FAILED, "clarification required before quoting", line_ids=unclear
        )
    if not items:
        raise TrollieError(ErrorCode.VALIDATION_FAILED, "the shopping list is empty")
    now = clock.now()
    address = owned_address(session, account_id, shopping.address_version_id)
    problem = build_problem(
        session,
        lines=_line_requests(items),
        zone=address.service_zone,
        now=now,
        loyalty_programmes=frozenset(verified_programmes(session, account_id)),
        deadline=shopping.deadline,
        budget_minor=shopping.budget_minor,
        allow_omit_optional=allow_omit_optional,
    )
    result = optimise(problem)
    must_have = {i.line_id for i in items if i.must_have}
    quotes: dict[Strategy, Quote | None] = {}
    seen: dict[tuple, Quote] = {}
    for strategy, option in result.options.items():
        if option is None:
            quotes[strategy] = None
            continue
        key = tuple((leg.location_id, leg.slot_id, leg.lines) for leg in option.legs)
        if key in seen:  # the same basket under two strategies is one estimate
            quotes[strategy] = seen[key]
            continue
        snapshot = {
            "schema": SCHEMA,
            "quote_id": uuid.uuid4(),
            "session_id": shopping.id,
            "account_id": shopping.account_id,
            "version": _next_version(session, shopping.id),
            "kind": QuoteKind.ESTIMATE,
            "currency": "ZAR",
            "simulated": True,
            "strategy": option.strategy,
            "policy_version": POLICY_VERSION,
            "proven_optimal": option.proven_optimal,
            "over_budget": option.over_budget,
            "destination": _destination(address),
            "fulfilment_policy": None,
            "funding_source": None,
            "legs": _snapshot_legs(session, option, must_have),
            "service_fee_minor": option.service_fee_minor,
            "tip_minor": 0,
            "discount_minor": sum(ln.discount_minor for leg in option.legs for ln in leg.lines),
            "goods_minor": option.goods_minor,
            "delivery_minor": option.delivery_minor,
            "total_minor": option.total_minor,
            "maximum_payable_minor": option.total_minor,
            "completion": option.completion,
            "coverage": {
                "requested_lines": len(items),
                "quoted_lines": sum(len(leg.lines) for leg in option.legs),
                "omitted_line_ids": list(result.omitted_line_ids),
            },
            "terms_version": TERMS_VERSION,
            "approval_policy_version": APPROVAL_POLICY_VERSION,
            "nonce": secrets.token_hex(16),
        }
        snapshot["expires_at"] = _dependency_expiry(session, _jsonable(snapshot), [])
        quotes[strategy] = seen[key] = _store_quote(
            session, shopping=shopping, snapshot=snapshot, derived_from=None
        )
    return EstimateResult(quotes, list(result.blocking), result.omitted_line_ids)


# --- Firm quotes ---------------------------------------------------------------------


@dataclass
class FirmResult:
    quote: Quote | None
    blocking: list[Blocking] = field(default_factory=list)


def _reservation_lines(leg: dict[str, Any]) -> list[ReservationLine]:
    return [
        ReservationLine(
            uuid.UUID(ln["product"]["id"]), ln["merchant_sku"], ln["units"], ln["unit_price_minor"]
        )
        for ln in leg["lines"]
    ]


def _validate_fulfilment(
    estimate: dict[str, Any], mode: FulfilmentMode, permitted_omissions: list[str]
) -> dict[str, Any]:
    lines = {ln["line_id"]: ln for leg in estimate["legs"] for ln in leg["lines"]}
    if mode is FulfilmentMode.COMPLETE_REQUIRED and permitted_omissions:
        raise TrollieError(
            ErrorCode.VALIDATION_FAILED, "a complete-required basket cannot permit omissions"
        )
    for line_id in permitted_omissions:
        if line_id not in lines:
            raise TrollieError(ErrorCode.VALIDATION_FAILED, "unknown line", line_id=line_id)
        if lines[line_id]["must_have"]:
            raise TrollieError(
                ErrorCode.VALIDATION_FAILED,
                "a must-have item cannot be a permitted omission",
                line_id=line_id,
            )
    return {
        "mode": mode,
        "permitted_omissions": sorted(permitted_omissions),
        "allow_new_merchants": False,
        "allow_new_items": False,
        "allow_quantity_increase": False,
        "allow_fee_increase": False,
        "allow_later_window": False,
    }


def _observe(
    merchant: MerchantAdapter,
    *,
    location_id: uuid.UUID,
    client_ref: str,
    lines: list[ReservationLine],
):
    """Call the merchant; on timeout, look the reservation up by our reference."""
    try:
        return merchant.prepare_reservation(
            location_id=location_id, client_ref=client_ref, lines=lines
        ), None
    except MerchantTimeout:
        try:
            return merchant.get_reservation(client_ref=client_ref), "timeout_then_lookup"
        except MerchantTimeout:
            return None, "timeout_lookup_failed"


def release_reservations(
    sessions: sessionmaker[Session], merchant: MerchantAdapter, reservation_ids: list[uuid.UUID]
) -> None:
    for rid in reservation_ids:
        with sessions() as s, s.begin():
            res = s.get(Reservation, rid, with_for_update=True)
            if res.state not in (ReservationState.HELD, ReservationState.UNKNOWN):
                continue
            res.state = ReservationState.RELEASE_REQUESTED
            res.version += 1
            client_ref = res.client_ref
        try:
            obs = merchant.release_reservation(client_ref=client_ref)
            final = (
                ReservationState.RELEASED
                if obs.status in ("released", "expired", "not_found")
                else ReservationState.RELEASE_REQUESTED
            )
        except MerchantTimeout:
            final = ReservationState.RELEASE_REQUESTED  # retried by reconciliation
        with sessions() as s, s.begin():
            res = s.get(Reservation, rid, with_for_update=True)
            res.state = final
            res.version += 1


def prepare_firm_quote(
    sessions: sessionmaker[Session],
    *,
    estimate_id: uuid.UUID,
    account_id: uuid.UUID,
    merchant: MerchantAdapter,
    clock: Clock,
    fulfilment_mode: FulfilmentMode,
    permitted_omissions: list[str],
    funding_source: str,
) -> FirmResult:
    # 1. Validate and persist reservation intents.
    with sessions() as s, s.begin():
        estimate = owned_quote(s, estimate_id, account_id, lock=True)
        if estimate.kind != QuoteKind.ESTIMATE or estimate.state != QuoteState.ESTIMATE:
            raise TrollieError(ErrorCode.INVALID_STATE_TRANSITION, "not an open estimate")
        if estimate.expires_at <= clock.now():
            raise TrollieError(ErrorCode.QUOTE_EXPIRED, "estimate expired; request new options")
        fulfilment = _validate_fulfilment(estimate.snapshot, fulfilment_mode, permitted_omissions)
        if funding_source not in PAY_PER_ORDER_SOURCES:
            kind = funding_source.split(":", 1)[0]
            if kind not in FUNDING_VALIDATORS:
                raise TrollieError(ErrorCode.CAPABILITY_NOT_ENABLED, "unsupported funding source")
            FUNDING_VALIDATORS[kind](s, account_id, funding_source, estimate.total_minor)
        snapshot = copy.deepcopy(estimate.snapshot)
        plans = []
        for leg in snapshot["legs"]:
            lines = _reservation_lines(leg)
            res = Reservation(
                location_id=uuid.UUID(leg["location_id"]),
                merchant_id=uuid.UUID(leg["seller"]["merchant_id"]),
                client_ref=f"res-{uuid.uuid4()}",
                lines=_jsonable([vars(ln) for ln in lines]),
                lines_hash=canonical_hash([vars(ln) for ln in lines]),
            )
            s.add(res)
            s.flush()
            plans.append((res.id, res.client_ref, res.location_id, lines))

    # 2. Call merchants outside any database transaction; persist each observation.
    held: list[uuid.UUID] = []
    blocking: list[Blocking] = []
    for rid, client_ref, location_id, lines in plans:
        obs, note = _observe(merchant, location_id=location_id, client_ref=client_ref, lines=lines)
        with sessions() as s, s.begin():
            res = s.get(Reservation, rid, with_for_update=True)
            if obs is None:
                res.state = ReservationState.UNKNOWN
            elif obs.status == "held":
                res.state, res.merchant_ref, res.expires_at = (
                    ReservationState.HELD,
                    obs.merchant_ref,
                    obs.expires_at,
                )
            else:
                res.state = ReservationState.REJECTED
            res.evidence = {
                "status": obs.status if obs else None,
                "reason": obs.reason if obs else None,
                "note": note,
                "observed_at": clock.now().isoformat(),
            }
            res.version += 1
            if res.state == ReservationState.HELD:
                held.append(rid)
            else:
                # T07: no hold means no firm claim, whatever stock was observed.
                blocking.append(
                    Blocking(
                        "reservation_not_held",
                        f"store {location_id} did not confirm a hold ({res.state})",
                    )
                )

    if blocking:
        # Release every hold we may have created, including UNKNOWN ones, by reference.
        release_reservations(sessions, merchant, [p[0] for p in plans])
        return FirmResult(None, blocking)

    # 3. All legs held: derive the firm quote from the estimate snapshot.
    with sessions() as s, s.begin():
        estimate = owned_quote(s, estimate_id, account_id, lock=True)
        superseded = estimate.state != QuoteState.ESTIMATE
        reservations = [s.get(Reservation, p[0]) for p in plans]
        if not superseded:
            shopping = s.get(ShoppingSession, estimate.session_id)
            for leg, res in zip(snapshot["legs"], reservations, strict=True):
                leg["reservation"] = {
                    "id": res.id,
                    "client_ref": res.client_ref,
                    "merchant_ref": res.merchant_ref,
                    "expires_at": res.expires_at,
                }
            snapshot.update(
                {
                    "quote_id": uuid.uuid4(),
                    "version": _next_version(s, estimate.session_id),
                    "kind": QuoteKind.FIRM,
                    "derived_from_quote_id": estimate.id,
                    "fulfilment_policy": fulfilment,
                    "funding_source": funding_source,
                    "nonce": secrets.token_hex(16),
                }
            )
            snapshot["expires_at"] = _dependency_expiry(s, _jsonable(snapshot), reservations)
            firm = _store_quote(s, shopping=shopping, snapshot=snapshot, derived_from=estimate.id)
            estimate.state = QuoteState.REPLACED
            estimate.state_version += 1
            estimate.replaced_by_id = firm.id
            audit(
                s,
                actor=f"account:{account_id}",
                action="quote.firm_created",
                object_type="quote",
                object_id=firm.id,
                derived_from=str(estimate.id),
            )
    if superseded:
        release_reservations(sessions, merchant, held)
        raise TrollieError(ErrorCode.INVALID_STATE_TRANSITION, "estimate changed concurrently")
    return FirmResult(firm)


# --- Expiry --------------------------------------------------------------------------


def expire_if_due(session: Session, quote: Quote, now: datetime) -> bool:
    """Project expiry. Returns True when the quote can no longer be approved or executed."""
    if quote.state in (QuoteState.ESTIMATE, QuoteState.FIRM, QuoteState.APPROVED) and (
        quote.expires_at <= now
    ):
        quote.state = QuoteState.EXPIRED
        quote.state_version += 1
        return True
    return quote.state in (
        QuoteState.EXPIRED,
        QuoteState.INVALIDATED,
        QuoteState.REPLACED,
        QuoteState.CONSUMED,
    )

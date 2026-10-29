"""Customer and agent endpoints (blueprint §10.1). Agents may propose items, request estimates
and submit purchase requests; they can never approve, pay or create orders."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.accounts.service import confirm_preference, propose_preference
from app.api.auth import Principal
from app.api.deps import AppContext, ctx, customer, db, principal
from app.api.schemas import (
    AssertionIn,
    ChallengeIn,
    EstimateIn,
    FirmIn,
    IssueIn,
    ItemIn,
    OrderIn,
    PreferenceIn,
    PurchaseRequestIn,
    SessionIn,
)
from app.approvals.service import (
    begin_approval,
    begin_registration,
    finish_registration,
    verify_approval,
)
from app.controls.service import audit
from app.durable import idempotency, outbox
from app.errors import ErrorCode, TrollieError
from app.orders.handlers import ingest_webhook
from app.orders.models import Order
from app.orders.service import create_order, create_refund, request_cancellation, start_checkout
from app.orders.status import order_status
from app.products.models import Product
from app.quotes.models import FulfilmentMode
from app.quotes.optimiser import Candidate, Quantity, Rule
from app.quotes.service import (
    add_item,
    create_session,
    owned_quote,
    prepare_firm_quote,
    request_estimates,
)

router = APIRouter(prefix="/v1")


def _quote_view(quote) -> dict[str, Any]:
    """Authoritative, server-side view of a quote. Never built from client input."""
    snap = quote.snapshot
    return {
        "quote_id": str(quote.id),
        "kind": quote.kind,
        "state": quote.state,
        "quote_hash": quote.quote_hash,
        "expires_at": quote.expires_at.isoformat(),
        "simulated": True,
        "strategy": snap["strategy"],
        "total_minor": snap["total_minor"],
        "maximum_payable_minor": snap["maximum_payable_minor"],
        "goods_minor": snap["goods_minor"],
        "delivery_minor": snap["delivery_minor"],
        "service_fee_minor": snap["service_fee_minor"],
        "funding_source": snap["funding_source"],
        "fulfilment_policy": snap["fulfilment_policy"],
        "destination": {k: snap["destination"][k] for k in ("label", "version", "service_zone")},
        "coverage": snap["coverage"],
        "over_budget": snap.get("over_budget", False),
        "legs": [
            {
                "leg_id": leg["leg_id"],
                "location_id": leg["location_id"],
                "seller": leg["seller"]["legal_name"],
                "display_name": leg["seller"]["display_name"],
                "goods_minor": leg["goods_minor"],
                "delivery_fee_minor": leg["delivery"]["fee_minor"],
                "window_start": leg["delivery"]["window_start"],
                "window_end": leg["delivery"]["window_end"],
                "reserved": leg["reservation"] is not None,
                "lines": [
                    {
                        "line_id": ln["line_id"],
                        "brand": ln["product"]["brand"],
                        "name": ln["product"]["name"],
                        "variant": ln["product"]["variant"],
                        "units": ln["units"],
                        "unit_price_minor": ln["unit_price_minor"],
                        "discount_minor": ln["discount_minor"],
                        "line_total_minor": ln["line_total_minor"],
                        "must_have": ln["must_have"],
                    }
                    for ln in leg["lines"]
                ],
            }
            for leg in snap["legs"]
        ],
    }


# --- Catalogue and lists -------------------------------------------------------------


@router.get("/catalogue/products")
def products(q: str = "", s: Session = Depends(db), p: Principal = Depends(principal)):
    query = select(Product).order_by(Product.category, Product.name)
    if q:
        query = query.where(or_(Product.name.ilike(f"%{q}%"), Product.brand.ilike(f"%{q}%")))
    return [
        {
            "product_id": str(x.id),
            "gtin": x.gtin,
            "brand": x.brand,
            "name": x.name,
            "variant": x.variant,
            "unit": x.unit,
            "unit_measure": x.unit_measure,
            "pack_count": x.pack_count,
            "category": x.category,
        }
        for x in s.scalars(query.limit(200))
    ]


@router.post("/shopping-sessions", status_code=201)
def new_session(body: SessionIn, s: Session = Depends(db), p: Principal = Depends(customer)):
    with s.begin():
        row = create_session(
            s,
            account_id=p.account_id,
            address_version_id=body.address_version_id,
            budget_minor=body.budget_minor,
            deadline=body.deadline,
        )
        return {"session_id": str(row.id)}


@router.post("/shopping-sessions/{session_id}/items", status_code=201)
def new_item(
    session_id: uuid.UUID, body: ItemIn, s: Session = Depends(db), p: Principal = Depends(principal)
):
    q = body.quantity
    try:
        quantity = Quantity(packs=q.packs, measure=q.measure, unit=q.unit)
    except ValueError as exc:
        raise TrollieError(ErrorCode.VALIDATION_FAILED, str(exc)) from exc
    with s.begin():
        item = add_item(
            s,
            session_id=session_id,
            account_id=p.account_id,
            line_id=body.line_id,
            rule=Rule(body.rule),
            candidates=[
                Candidate(c.product_id, c.rank, c.max_unit_price_minor) for c in body.candidates
            ],
            quantity=quantity,
            must_have=body.must_have,
            source=p.kind,
            needs_clarification=body.needs_clarification,
        )
        return {"item_id": str(item.id), "line_id": item.line_id, "source": item.source}


@router.post("/shopping-sessions/{session_id}/quotes")
def estimates(
    session_id: uuid.UUID,
    body: EstimateIn,
    s: Session = Depends(db),
    p: Principal = Depends(principal),
    c: AppContext = Depends(ctx),
):
    with s.begin():
        result = request_estimates(
            s,
            session_id=session_id,
            account_id=p.account_id,
            clock=c.rt.clock,
            allow_omit_optional=body.allow_omit_optional,
        )
        return {
            "options": {k: (_quote_view(v) if v else None) for k, v in result.quotes.items()},
            "blocking": [vars(b) for b in result.blocking],
            "omitted_line_ids": list(result.omitted_line_ids),
            "note": "Estimates are not purchasable. Request a firm quote to reserve stock.",
        }


@router.post("/quotes/{quote_id}/firm")
def firm(
    quote_id: uuid.UUID,
    body: FirmIn,
    p: Principal = Depends(customer),
    c: AppContext = Depends(ctx),
):
    result = prepare_firm_quote(
        c.rt.sessions,
        estimate_id=quote_id,
        account_id=p.account_id,
        merchant=c.rt.merchant,
        clock=c.rt.clock,
        fulfilment_mode=FulfilmentMode(body.fulfilment_mode),
        permitted_omissions=body.permitted_omissions,
        funding_source=body.funding_source,
    )
    if result.quote is None:
        return JSONResponse(
            status_code=409,
            content={"code": "RESERVATION_FAILED", "blocking": [vars(b) for b in result.blocking]},
        )
    return _quote_view(result.quote)


@router.get("/quotes/{quote_id}")
def get_quote(quote_id: uuid.UUID, s: Session = Depends(db), p: Principal = Depends(principal)):
    return _quote_view(owned_quote(s, quote_id, p.account_id))


@router.post("/purchase-requests", status_code=202)
def purchase_request(
    body: PurchaseRequestIn, s: Session = Depends(db), p: Principal = Depends(principal)
):
    """Bring a quote to the owner's attention. Creates no authority of any kind."""
    with s.begin():
        quote = owned_quote(s, body.quote_id, p.account_id)
        outbox.emit(
            s,
            aggregate_type="quote",
            aggregate_id=quote.id,
            aggregate_version=1,
            event_type="purchase.requested",
            payload={"by": p.actor},
        )
        audit(
            s,
            actor=p.actor,
            action="purchase.request",
            object_type="quote",
            object_id=quote.id,
            note=body.note or "",
        )
    return {
        "quote_id": str(quote.id),
        "approval_page": f"/approve/quote/{quote.id}",
        "status": "awaiting_owner_approval",
    }


# --- Passkeys and approvals ----------------------------------------------------------


@router.post("/passkeys/registration-options")
def registration_options(
    s: Session = Depends(db), p: Principal = Depends(customer), c: AppContext = Depends(ctx)
):
    with s.begin():
        challenge_id, options = begin_registration(
            s,
            c.webauthn,
            account_id=p.account_id,
            display_name="Trollie customer",
            clock=c.rt.clock,
        )
    return {"challenge_id": str(challenge_id), "options": options}


@router.post("/passkeys", status_code=201)
def register_passkey(
    body: AssertionIn,
    s: Session = Depends(db),
    p: Principal = Depends(customer),
    c: AppContext = Depends(ctx),
):
    with s.begin():
        cred = finish_registration(
            s,
            c.webauthn,
            account_id=p.account_id,
            challenge_id=body.challenge_id,
            credential=body.credential,
            clock=c.rt.clock,
        )
        return {"credential": str(cred.id)}


@router.post("/approval-challenges")
def approval_challenge(
    body: ChallengeIn,
    s: Session = Depends(db),
    p: Principal = Depends(customer),
    c: AppContext = Depends(ctx),
):
    with s.begin():
        challenge_id, options = begin_approval(
            s,
            c.webauthn,
            account_id=p.account_id,
            subject_type=body.subject_type,
            subject_id=body.subject_id,
            clock=c.rt.clock,
        )
    return {"challenge_id": str(challenge_id), "options": options}


@router.post("/quotes/{quote_id}/approval-challenges")
def quote_challenge(
    quote_id: uuid.UUID,
    s: Session = Depends(db),
    p: Principal = Depends(customer),
    c: AppContext = Depends(ctx),
):
    return approval_challenge(ChallengeIn(subject_type="quote", subject_id=quote_id), s, p, c)


@router.post("/approvals", status_code=201)
def approvals(
    body: AssertionIn,
    s: Session = Depends(db),
    p: Principal = Depends(customer),
    c: AppContext = Depends(ctx),
):
    with s.begin():
        approval = verify_approval(
            s,
            c.webauthn,
            account_id=p.account_id,
            challenge_id=body.challenge_id,
            credential=body.credential,
            clock=c.rt.clock,
        )
        return {
            "approval_id": str(approval.id),
            "subject_type": approval.subject_type,
            "subject_id": str(approval.subject_id),
        }


# --- Orders --------------------------------------------------------------------------


@router.post("/orders", status_code=201)
def orders(
    body: OrderIn,
    idempotency_key: str = Header(...),
    s: Session = Depends(db),
    p: Principal = Depends(customer),
    c: AppContext = Depends(ctx),
):
    with s.begin():
        op = idempotency.begin(
            s,
            scope=f"orders.create:{p.account_id}",
            key=idempotency_key,
            request={"approval_id": str(body.approval_id)},
        )
        if op.replay:
            return op.response
    order_id = create_order(c.rt, account_id=p.account_id, approval_id=body.approval_id)
    response = {"order_id": str(order_id)}
    with s.begin():
        idempotency.begin(
            s,
            scope=f"orders.create:{p.account_id}",
            key=idempotency_key,
            request={"approval_id": str(body.approval_id)},
        ).complete(response)
    return response


@router.post("/orders/{order_id}/checkout-sessions")
def checkout(order_id: uuid.UUID, p: Principal = Depends(customer), c: AppContext = Depends(ctx)):
    ref = start_checkout(c.rt, account_id=p.account_id, order_id=order_id)
    return {
        "checkout_ref": ref,
        "checkout_url": f"sim://checkout/{ref}" if ref else None,
        "note": "Provider-hosted checkout (simulated). No card data passes through Trollie.",
    }


@router.get("/orders/{order_id}")
def get_order(order_id: uuid.UUID, s: Session = Depends(db), p: Principal = Depends(principal)):
    return order_status(s, order_id, p.account_id)


@router.post("/orders/{order_id}/cancellation-requests", status_code=202)
def cancel(order_id: uuid.UUID, p: Principal = Depends(customer), c: AppContext = Depends(ctx)):
    return {"status": request_cancellation(c.rt, account_id=p.account_id, order_id=order_id)}


@router.post("/orders/{order_id}/issues", status_code=202)
def issue(
    order_id: uuid.UUID,
    body: IssueIn,
    idempotency_key: str = Header(...),
    s: Session = Depends(db),
    p: Principal = Depends(customer),
    c: AppContext = Depends(ctx),
):
    """A missing/damaged item attributable to one leg's seller becomes a refund case."""
    order = s.get(Order, order_id)
    if order is None or order.account_id != p.account_id:
        raise TrollieError(ErrorCode.NOT_FOUND, "order not found")
    snap = order_status(s, order_id, p.account_id)
    leg = next((lg for lg in snap["legs"] if lg["leg_id"] == body.leg_id), None)
    if leg is None:
        raise TrollieError(ErrorCode.VALIDATION_FAILED, "unknown leg")
    parties = [
        {
            "party_type": "merchant",
            "party_id": leg["merchant_id"],
            "amount_minor": body.amount_minor,
            "leg_id": body.leg_id,
            "line_id": body.line_id,
        }
    ]
    key = f"issue:{order_id}:{idempotency_key}"
    s.rollback()
    if order.funding_source.startswith("wallet:"):
        from app.wallet.orders import refund_wallet_order

        refund_id = refund_wallet_order(c.rt, order_id=order_id, business_key=key, parties=parties)
    else:
        refund_id = create_refund(
            c.rt, order_id=order_id, business_key=key, parties=parties, reason=body.reason
        )
    return {"refund_id": str(refund_id), "status": "refund_requested"}


# --- Preferences ---------------------------------------------------------------------


@router.post("/preferences", status_code=201)
def preferences(
    body: PreferenceIn,
    s: Session = Depends(db),
    p: Principal = Depends(principal),
    c: AppContext = Depends(ctx),
):
    with s.begin():
        pref = propose_preference(
            s,
            account_id=p.account_id,
            rule=body.rule,
            provenance=p.kind,
            product_id=body.product_id,
            category=body.category,
            now=c.rt.clock.now(),
        )
        return {"preference_id": str(pref.id), "confirmed": pref.confirmed_at is not None}


@router.post("/preferences/{preference_id}/confirm")
def confirm(
    preference_id: uuid.UUID,
    s: Session = Depends(db),
    p: Principal = Depends(customer),
    c: AppContext = Depends(ctx),
):
    with s.begin():
        confirm_preference(
            s, account_id=p.account_id, preference_id=preference_id, now=c.rt.clock.now()
        )
    return {"confirmed": True}


# --- Provider callbacks --------------------------------------------------------------


@router.post("/webhooks/simpay")
async def simpay_webhook(request: Request, c: AppContext = Depends(ctx)):
    body = await request.body()  # verified over the exact raw bytes before parsing
    result = ingest_webhook(
        c.rt,
        body,
        request.headers.get("x-simpay-signature"),
        request.headers.get("x-simpay-timestamp"),
    )
    status = 400 if result.status == "rejected" else 200
    return JSONResponse(status_code=status, content={"status": result.status})

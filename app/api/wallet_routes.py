"""Synthetic wallet, agent and grant endpoints. SIMULATED — NOT REAL MONEY."""

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.auth import Principal, issue
from app.api.deps import AppContext, ctx, customer, db, principal
from app.api.schemas import AgentIn, AmountIn, ExecuteIn, GrantIn
from app.errors import ErrorCode, TrollieError
from app.wallet import service as wallet
from app.wallet.grants import create_grant, revoke_grant
from app.wallet.models import Agent
from app.wallet.orders import execute_under_mandate

router = APIRouter(prefix="/v1")


@router.post("/wallet", status_code=201)
def open_wallet(s: Session = Depends(db), p: Principal = Depends(customer)):
    with s.begin():
        w = wallet.open_wallet(s, account_id=p.account_id)
        return {
            "wallet_id": str(w.id),
            "funding_reference": w.funding_reference,
            "label": "SIMULATED — NOT REAL MONEY",
        }


@router.get("/wallet")
def get_wallet(s: Session = Depends(db), p: Principal = Depends(customer)):
    with s.begin():
        w = wallet.wallet_for(s, p.account_id)
        return {
            "wallet_id": str(w.id),
            "funding_reference": w.funding_reference,
            **wallet.balances(s, w.id),
        }


@router.post("/wallet/topups", status_code=201)
def topup(body: AmountIn, s: Session = Depends(db), p: Principal = Depends(customer)):
    """Record the intent. Only a verified provider confirmation makes funds spendable."""
    with s.begin():
        w = wallet.wallet_for(s, p.account_id)
        intent = wallet.create_funding_intent(s, wallet_id=w.id, amount_minor=body.amount_minor)
        return {
            "transfer_ref": intent.transfer_ref,
            "funding_reference": w.funding_reference,
            "pay_to": wallet.COLLECTION_ACCOUNT,
            "state": intent.state,
        }


@router.post("/agents", status_code=201)
def new_agent(
    body: AgentIn,
    s: Session = Depends(db),
    p: Principal = Depends(customer),
    c: AppContext = Depends(ctx),
):
    """Create an agent with its own exclusive envelope, and return the agent's token."""
    with s.begin():
        agent = Agent(account_id=p.account_id, name=body.name)
        s.add(agent)
        s.flush()
        envelope = wallet.create_envelope(
            s, owner_account_id=p.account_id, agent_id=agent.id, label=body.name
        )
        token = issue(c.session_secret, Principal("agent", p.account_id, agent.id))
        return {"agent_id": str(agent.id), "envelope_id": str(envelope.id), "agent_token": token}


@router.post("/wallet/envelopes/{envelope_id}/allocations", status_code=201)
def allocate(
    envelope_id: uuid.UUID,
    body: AmountIn,
    idempotency_key: str = Header(...),
    s: Session = Depends(db),
    p: Principal = Depends(customer),
):
    with s.begin():
        wallet.allocate(
            s,
            owner_account_id=p.account_id,
            envelope_id=envelope_id,
            amount_minor=body.amount_minor,
            business_key=f"{p.account_id}:{idempotency_key}",
        )
    return {"allocated_minor": body.amount_minor}


@router.post("/wallet/redemptions", status_code=201)
def redeem(
    body: AmountIn,
    idempotency_key: str = Header(...),
    s: Session = Depends(db),
    p: Principal = Depends(customer),
    c: AppContext = Depends(ctx),
):
    with s.begin():
        r = wallet.request_redemption(
            s,
            owner_account_id=p.account_id,
            amount_minor=body.amount_minor,
            business_key=f"{p.account_id}:{idempotency_key}",
            now=c.rt.clock.now(),
        )
        return {
            "redemption_id": str(r.id),
            "state": r.state,
            "destination": "verified original funding source (simulated)",
        }


@router.post("/agents/{agent_id}/grants", status_code=201)
def grant(
    agent_id: uuid.UUID,
    body: GrantIn,
    s: Session = Depends(db),
    p: Principal = Depends(customer),
    c: AppContext = Depends(ctx),
):
    """Only the owner creates or broadens a grant; a mandate still needs passkey approval."""
    now = c.rt.clock.now()
    with s.begin():
        g = create_grant(
            s,
            owner_account_id=p.account_id,
            agent_id=agent_id,
            approval_mode=body.approval_mode,
            address_version_id=body.address_version_id,
            per_order_cap_minor=body.per_order_cap_minor,
            period_cap_minor=body.period_cap_minor,
            period_days=body.period_days,
            max_orders_per_day=body.max_orders_per_day,
            valid_from=now,
            valid_until=now + timedelta(days=body.valid_days),
            merchant_ids=body.merchant_ids,
            product_ids=body.product_ids,
            categories=body.categories,
            purpose=body.purpose,
        )
        return {
            "grant_id": str(g.id),
            "version": g.version,
            "status": g.status,
            "approval_page": f"/approve/mandate/{g.id}" if g.approval_mode == "mandate" else None,
        }


@router.delete("/grants/{grant_id}", status_code=200)
def revoke(
    grant_id: uuid.UUID,
    s: Session = Depends(db),
    p: Principal = Depends(customer),
    c: AppContext = Depends(ctx),
):
    with s.begin():
        revoke_grant(s, owner_account_id=p.account_id, grant_id=grant_id, now=c.rt.clock.now())
    return {"status": "revoked"}


@router.post("/agent/executions", status_code=201)
def execute(body: ExecuteIn, p: Principal = Depends(principal), c: AppContext = Depends(ctx)):
    """An agent asks the trusted executor to run a quote under its approved mandate."""
    if p.kind != "agent":
        raise TrollieError(ErrorCode.AUTHORITY_DENIED, "only an agent executes under a mandate")
    order_id = execute_under_mandate(c.rt, agent_id=p.agent_id, quote_id=body.quote_id)
    return {"order_id": str(order_id)}

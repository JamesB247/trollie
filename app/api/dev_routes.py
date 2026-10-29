"""Development harness: fictional accounts, simulator controls, merchant/courier actions and
ledger checks. Disabled outside dev/test. These endpoints stand in for external parties
(the customer's bank app, the merchant's device, the courier) — they are not Trollie APIs."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounts.models import CustomerAccount
from app.accounts.service import add_address_version
from app.api.auth import Principal, issue
from app.api.deps import AppContext, db, dev_only
from app.api.schemas import Strict
from app.ledger.models import LedgerAccount, LedgerEntry
from app.orders.handlers import pump
from app.orders.models import DeliveryJob, Order, OrderLeg
from app.orders.service import courier_progress, merchant_ready
from app.payments.settlement import import_settlement
from app.seed import seed
from app.simulators.faults import inject
from app.wallet.service import COLLECTION_ACCOUNT

router = APIRouter(prefix="/v1/dev", tags=["dev"])


class AccountIn(Strict):
    display_name: str = "Demo Household (Fictional)"
    # Any delivery zone the seeded data serves (zone-a/zone-b, or a market zone).
    zone: str = Field(default="zone-a", pattern=r"^[a-z0-9-]{1,40}$")
    address_text: str = "1 Fictional Lane, Synthetic Township"


class CompleteIn(Strict):
    approve: bool = True


class TransferIn(Strict):
    transfer_ref: str
    reference: str
    amount_minor: int = Field(gt=0, le=10**12)
    status: Literal["confirmed", "pending", "failed", "reversed"] = "confirmed"
    currency: str = "ZAR"
    destination_account: str = COLLECTION_ACCOUNT
    deliveries: int = Field(default=1, ge=1, le=5)


class FaultIn(Strict):
    system: Literal["merchant", "payment", "courier"]
    target: str
    operation: str
    mode: str
    times: int = Field(default=1, ge=1, le=100)


@router.post("/seed")
def dev_seed(
    market: Literal["none", "true", "small", "large"] = "none",
    c: AppContext = Depends(dev_only),
):
    """Seed the base fixture; `market=small` (or `true`) adds the 90-product crowd market,
    `market=large` the ~63 000-product catalogue-scale market (I-043)."""
    from app.simulators.bigmarket import seed_bigmarket
    from app.simulators.market import seed_market
    from app.simulators.merchant import restock

    large = None
    with c.rt.sessions() as s, s.begin():
        ids = seed(s, now=c.rt.clock.now())
        if market in ("true", "small"):
            ids |= seed_market(s, now=c.rt.clock.now())
        elif market == "large":
            large = seed_bigmarket(s, now=c.rt.clock.now())
        restocked = restock(s)
    return {
        "merchants": sorted(k for k in ids if k.startswith("merchant:")),
        "restocked_rows": restocked,
        "large_market": large,
    }


@router.post("/accounts", status_code=201)
def dev_account(body: AccountIn, c: AppContext = Depends(dev_only)):
    from app.api.app_factory import address_cipher

    with c.rt.sessions() as s, s.begin():
        acct = CustomerAccount(id=uuid.uuid4(), display_name=body.display_name)
        s.add(acct)
        s.flush()
        addr = add_address_version(
            s,
            address_cipher(),
            account_id=acct.id,
            label="Home",
            address_text=body.address_text,
            service_zone=body.zone,
        )
        token = issue(c.session_secret, Principal("customer", acct.id))
        return {
            "account_id": str(acct.id),
            "address_version_id": str(addr.id),
            "token": token,
            "login_url": f"/dev/login?token={token}",
        }


@router.post("/sim/checkouts/{provider_ref}/complete")
def complete_checkout(provider_ref: str, body: CompleteIn, c: AppContext = Depends(dev_only)):
    """Stand-in for the customer finishing 3DS or the bank-app step."""
    c.rt.payments.customer_completes(provider_ref, approve=body.approve)
    pump(c.rt, c.rt.payments)
    return {"status": "submitted"}


@router.post("/sim/transfers")
def transfer(body: TransferIn, c: AppContext = Depends(dev_only)):
    """Stand-in for a bank transfer arriving at the collection account."""
    event_id = c.rt.payments.incoming_transfer(**body.model_dump())
    pump(c.rt, c.rt.payments)
    return {"event_id": event_id}


@router.post("/sim/faults", status_code=201)
def fault(body: FaultIn, c: AppContext = Depends(dev_only)):
    with c.rt.sessions() as s, s.begin():
        inject(
            s,
            system=body.system,
            target=body.target,
            operation=body.operation,
            mode=body.mode,
            times=body.times,
        )
    return {"status": "armed"}


@router.delete("/sim/faults")
def clear_faults(c: AppContext = Depends(dev_only)):
    from sqlalchemy import delete

    from app.simulators.models import SimFault

    with c.rt.sessions() as s, s.begin():
        s.execute(delete(SimFault))
    return {"status": "cleared"}


class WorkerIn(Strict):
    paused: bool


@router.post("/worker")
def worker(body: WorkerIn, c: AppContext = Depends(dev_only)):
    c.rt.worker_paused = body.paused
    return {"paused": c.rt.worker_paused}


@router.post("/pump")
def dev_pump(c: AppContext = Depends(dev_only)):
    pump(c.rt, c.rt.payments)
    return {"status": "ok"}


@router.post("/merchant/legs/{leg_id}/ready")
def ready(leg_id: uuid.UUID, c: AppContext = Depends(dev_only)):
    merchant_ready(c.rt, leg_id=leg_id)
    return {"status": "ready"}


@router.post("/courier/jobs/{job_id}/{to}")
def courier(
    job_id: uuid.UUID,
    to: Literal["collected", "delivered", "failed"],
    c: AppContext = Depends(dev_only),
):
    courier_progress(c.rt, job_id=job_id, to=to)
    return {"status": to}


@router.get("/orders/{order_id}/fulfilment")
def fulfilment(order_id: uuid.UUID, s: Session = Depends(db), c: AppContext = Depends(dev_only)):
    legs = s.scalars(select(OrderLeg).where(OrderLeg.order_id == order_id)).all()
    out = []
    for leg in legs:
        job = s.scalars(select(DeliveryJob).where(DeliveryJob.order_leg_id == leg.id)).first()
        out.append(
            {
                "leg_id": leg.leg_id,
                "order_leg_id": str(leg.id),
                "state": leg.state,
                "delivery_job_id": str(job.id) if job else None,
                "delivery_state": job.state if job else None,
            }
        )
    return {"order_id": str(order_id), "state": s.get(Order, order_id).state, "legs": out}


@router.post("/settlement-reports")
def settlement(c: AppContext = Depends(dev_only)):
    report = c.rt.payments.settlement_report(f"rpt-{uuid.uuid4()}")
    return {
        "report_ref": report["report_ref"],
        "lines": len(report["lines"]),
        "result": import_settlement(c.rt, report),
    }


@router.get("/ledger/trial-balance")
def trial_balance(s: Session = Depends(db), c: AppContext = Depends(dev_only)):
    """Debits equal credits overall and per transaction; balances by account code."""
    totals = s.execute(
        select(
            func.coalesce(func.sum(LedgerEntry.debit_minor), 0),
            func.coalesce(func.sum(LedgerEntry.credit_minor), 0),
        )
    ).one()
    unbalanced = s.execute(
        select(LedgerEntry.transaction_id)
        .group_by(LedgerEntry.transaction_id, LedgerEntry.currency)
        .having(func.sum(LedgerEntry.debit_minor) != func.sum(LedgerEntry.credit_minor))
    ).all()
    by_code = s.execute(
        select(LedgerAccount.code, func.sum(LedgerEntry.debit_minor - LedgerEntry.credit_minor))
        .join(LedgerEntry, LedgerEntry.account_id == LedgerAccount.id)
        .group_by(LedgerAccount.code)
        .order_by(LedgerAccount.code)
    ).all()
    return {
        "simulated": True,
        "debits_minor": int(totals[0]),
        "credits_minor": int(totals[1]),
        "balanced": int(totals[0]) == int(totals[1]) and not unbalanced,
        "unbalanced_transactions": [str(r[0]) for r in unbalanced],
        "net_by_code_minor": {code: int(net) for code, net in by_code},
    }

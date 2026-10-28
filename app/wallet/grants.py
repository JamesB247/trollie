"""Agent grants and the bounded mandate fixture (D-W03; DECISIONS.md A2).

- Only the owner can create, broaden or revoke a grant; each change is a new version.
- A mandate grant is inactive until the owner approves its exact hash with a passkey.
- Executing under a mandate is enabled only when the runtime allows the fixture
  (TROLLIE_ENV=test and TROLLIE_MANDATE_FIXTURE_ENABLED=true); the trusted executor checks
  every condition under lock. The agent can request execution; it cannot approve or post.
- Authority counters (per-period spend, orders per day) are never restored by refunds.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.approvals.models import Approval
from app.controls.service import audit
from app.durable.hashing import canonical_hash
from app.errors import ErrorCode, TrollieError
from app.products.models import Product
from app.quotes.models import Quote, QuoteKind, QuoteState
from app.quotes.service import recompute_hash
from app.wallet.models import Agent, Envelope, Grant, GrantUsage, MandateExecution, Wallet

AGENT_FORBIDDEN = {
    "allocate_funds",
    "broaden_grant",
    "change_address",
    "change_payee",
    "approve_quote",
    "post_ledger",
}


def deny_agent_action(s: Session, *, agent_id: uuid.UUID, action: str, **details) -> None:
    """Every attempt by an agent to widen its own authority is refused and audited (W08)."""
    audit(
        s,
        actor=f"agent:{agent_id}",
        action=f"agent.{action}",
        object_type="agent",
        object_id=agent_id,
        result="denied",
        **details,
    )
    raise TrollieError(
        ErrorCode.AUTHORITY_DENIED, "agents cannot perform this action", action=action
    )


def _owner_of_envelope(s: Session, envelope_id: uuid.UUID) -> uuid.UUID:
    envelope = s.get(Envelope, envelope_id)
    return s.get(Wallet, envelope.wallet_id).account_id


def grant_payload(g: Grant) -> dict:
    return {
        "agent_id": g.agent_id,
        "envelope_id": g.envelope_id,
        "version": g.version,
        "approval_mode": g.approval_mode,
        "merchant_ids": sorted(map(str, g.merchant_ids)),
        "product_ids": sorted(map(str, g.product_ids)),
        "categories": sorted(g.categories),
        "address_version_id": g.address_version_id,
        "per_order_cap_minor": g.per_order_cap_minor,
        "period_cap_minor": g.period_cap_minor,
        "period_days": g.period_days,
        "max_orders_per_day": g.max_orders_per_day,
        "valid_from": g.valid_from,
        "valid_until": g.valid_until,
        "purpose": g.purpose,
    }


def create_grant(
    s: Session,
    *,
    owner_account_id: uuid.UUID,
    agent_id: uuid.UUID,
    approval_mode: str,
    address_version_id: uuid.UUID,
    per_order_cap_minor: int,
    period_cap_minor: int,
    valid_from: datetime,
    valid_until: datetime,
    merchant_ids: list[uuid.UUID] = (),
    product_ids: list[uuid.UUID] = (),
    categories: list[str] = (),
    period_days: int = 7,
    max_orders_per_day: int = 3,
    purpose: str = "household groceries",
) -> Grant:
    agent = s.get(Agent, agent_id)
    if agent is None or agent.account_id != owner_account_id:
        raise TrollieError(ErrorCode.NOT_FOUND, "agent not found")
    envelope = s.scalars(select(Envelope).where(Envelope.agent_id == agent_id)).one_or_none()
    if envelope is None or _owner_of_envelope(s, envelope.id) != owner_account_id:
        raise TrollieError(ErrorCode.VALIDATION_FAILED, "agent has no envelope")
    if approval_mode not in ("per_quote", "mandate"):
        raise TrollieError(ErrorCode.VALIDATION_FAILED, "unknown approval mode")
    current = s.scalars(
        select(Grant)
        .where(Grant.agent_id == agent_id, Grant.status.in_(["active", "pending_approval"]))
        .with_for_update()
    ).all()
    version = (s.scalar(select(func.max(Grant.version)).where(Grant.agent_id == agent_id)) or 0) + 1
    grant = Grant(
        agent_id=agent_id,
        envelope_id=envelope.id,
        version=version,
        approval_mode=approval_mode,
        merchant_ids=list(merchant_ids),
        product_ids=list(product_ids),
        categories=list(categories),
        address_version_id=address_version_id,
        per_order_cap_minor=per_order_cap_minor,
        period_cap_minor=period_cap_minor,
        period_days=period_days,
        max_orders_per_day=max_orders_per_day,
        valid_from=valid_from,
        valid_until=valid_until,
        purpose=purpose,
        grant_hash="",
        status="active" if approval_mode == "per_quote" else "pending_approval",
    )
    grant.grant_hash = canonical_hash(grant_payload(grant))
    for old in current:  # a new version supersedes the old one
        old.status = "superseded"
    s.add(grant)
    s.flush()
    audit(
        s,
        actor=f"account:{owner_account_id}",
        action="grant.create",
        object_type="grant",
        object_id=grant.id,
        version=version,
        mode=approval_mode,
    )
    return grant


def revoke_grant(
    s: Session, *, owner_account_id: uuid.UUID, grant_id: uuid.UUID, now: datetime
) -> None:
    grant = s.get(Grant, grant_id, with_for_update=True)
    if grant is None or _owner_of_envelope(s, grant.envelope_id) != owner_account_id:
        raise TrollieError(ErrorCode.NOT_FOUND, "grant not found")
    grant.status = "revoked"
    grant.revoked_at = now
    audit(
        s,
        actor=f"account:{owner_account_id}",
        action="grant.revoke",
        object_type="grant",
        object_id=grant.id,
    )


def active_grant(s: Session, agent_id: uuid.UUID, *, lock: bool = False) -> Grant | None:
    q = select(Grant).where(Grant.agent_id == agent_id, Grant.status == "active")
    return s.scalars(q.with_for_update() if lock else q).one_or_none()


def grant_for_envelope(s: Session, envelope_id: uuid.UUID) -> Grant | None:
    return s.scalars(
        select(Grant).where(Grant.envelope_id == envelope_id, Grant.status == "active")
    ).one_or_none()


class MandateSubject:
    """A mandate version as an approval subject for the passkey ceremony (A2)."""

    def current_hash(
        self,
        session: Session,
        account_id: uuid.UUID,
        subject_id: uuid.UUID,
        now: datetime,
        *,
        lock: bool,
    ) -> tuple[str, datetime]:
        grant = session.get(Grant, subject_id, with_for_update=lock)
        if grant is None or _owner_of_envelope(session, grant.envelope_id) != account_id:
            raise TrollieError(ErrorCode.NOT_FOUND, "mandate not found")
        if grant.approval_mode != "mandate" or grant.status != "pending_approval":
            raise TrollieError(ErrorCode.INVALID_STATE_TRANSITION, "mandate not awaiting approval")
        if grant.valid_until <= now:
            raise TrollieError(ErrorCode.QUOTE_EXPIRED, "mandate validity has ended")
        if canonical_hash(grant_payload(grant)) != grant.grant_hash:
            raise TrollieError(ErrorCode.REAPPROVAL_REQUIRED, "mandate integrity check failed")
        return grant.grant_hash, grant.valid_until

    def on_approved(self, session: Session, subject_id: uuid.UUID, approval: Approval) -> None:
        grant = session.get(Grant, subject_id)
        grant.status = "active"
        grant.approval_id = approval.id


def check_mandate(s: Session, grant: Grant, quote: Quote, now: datetime) -> None:
    """Every condition of the approved mandate must hold for this exact quote."""

    def deny(reason: str) -> None:
        raise TrollieError(
            ErrorCode.AUTHORITY_DENIED, "outside the approved mandate", reason=reason
        )

    if grant.approval_mode != "mandate" or grant.status != "active" or grant.approval_id is None:
        deny("mandate_not_active")
    if not (grant.valid_from <= now < grant.valid_until):
        deny("outside_validity_window")
    snap = quote.snapshot
    if snap["funding_source"] != f"wallet:envelope:{grant.envelope_id}":
        deny("funding_source_not_mandate_envelope")
    if snap["destination"]["address_version_id"] != str(grant.address_version_id):
        deny("destination_not_approved")
    merchants = {leg["seller"]["merchant_id"] for leg in snap["legs"]}
    if grant.merchant_ids and not merchants <= set(map(str, grant.merchant_ids)):
        deny("merchant_not_permitted")
    products = {ln["product"]["id"] for leg in snap["legs"] for ln in leg["lines"]}
    allowed_products = set(map(str, grant.product_ids))
    if grant.categories:
        allowed_products |= {
            str(p)
            for p in s.scalars(select(Product.id).where(Product.category.in_(grant.categories)))
        }
    if (grant.product_ids or grant.categories) and not products <= allowed_products:
        deny("item_not_permitted")
    if quote.maximum_payable_minor > grant.per_order_cap_minor:
        deny("per_order_cap")
    period_start = now - timedelta(days=grant.period_days)
    spent = s.scalar(
        select(func.coalesce(func.sum(GrantUsage.amount_minor), 0)).where(
            GrantUsage.grant_id == grant.id, GrantUsage.used_at > period_start
        )
    )
    if spent + quote.maximum_payable_minor > grant.period_cap_minor:
        deny("period_cap")  # W15: splitting into small orders does not evade this
    today = s.scalar(
        select(func.count())
        .select_from(GrantUsage)
        .where(GrantUsage.grant_id == grant.id, GrantUsage.used_at > now - timedelta(days=1))
    )
    if today >= grant.max_orders_per_day:
        deny("velocity")


def authorise_under_mandate(
    s: Session, *, agent_id: uuid.UUID, quote_id: uuid.UUID, now: datetime
) -> MandateExecution:
    """Trusted executor: lock the grant, check the quote, record usage and authority."""
    grant = active_grant(s, agent_id, lock=True)
    if grant is None:
        raise TrollieError(ErrorCode.AUTHORITY_DENIED, "no active grant", reason="no_grant")
    quote = s.get(Quote, quote_id, with_for_update=True, populate_existing=True)
    if quote is None or quote.account_id != _owner_of_envelope(s, grant.envelope_id):
        raise TrollieError(ErrorCode.NOT_FOUND, "quote not found")
    if quote.kind != QuoteKind.FIRM or quote.state != QuoteState.FIRM or quote.expires_at <= now:
        raise TrollieError(ErrorCode.INVALID_STATE_TRANSITION, "quote is not executable")
    if recompute_hash(quote) != quote.quote_hash:
        raise TrollieError(ErrorCode.REAPPROVAL_REQUIRED, "quote integrity check failed")
    check_mandate(s, grant, quote, now)
    s.add(
        GrantUsage(
            grant_id=grant.id,
            quote_id=quote.id,
            amount_minor=quote.maximum_payable_minor,
            used_at=now,
        )
    )
    execution = MandateExecution(grant_id=grant.id, quote_id=quote.id, quote_hash=quote.quote_hash)
    s.add(execution)
    quote.state = QuoteState.APPROVED
    quote.state_version += 1
    s.flush()
    audit(
        s,
        actor=f"agent:{agent_id}",
        action="mandate.execute",
        object_type="quote",
        object_id=quote.id,
        grant_id=str(grant.id),
    )
    return execution

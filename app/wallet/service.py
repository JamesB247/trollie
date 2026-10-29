"""Synthetic wallet money movements (D-W01, D-W02, A4, A5). SIMULATED — NOT REAL MONEY.

Rules:
- Balances are derived from the ledger only; there is no editable balance column.
- Every movement locks the wallet row first, so all money operations on one wallet are
  serialised and balance checks cannot race (W04, W05, W14).
- Every posting key is derived from the business event, so repeats post once (W01, W11).
- Funding is not purchase consent; pending, failed or unverified funds are never spendable.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.controls.service import audit
from app.errors import ErrorCode, TrollieError
from app.ledger import chart
from app.ledger.postings import recipient_account
from app.ledger.service import account, balance, credit, debit, post
from app.reconciliation.service import open_case
from app.wallet.models import (
    Envelope,
    FundingIntent,
    Redemption,
    Wallet,
    WalletRefund,
    WalletReservation,
)

COLLECTION_ACCOUNT = "trollie-sim-collection"  # where simulated top-ups must arrive


# --- Accounts and locking ------------------------------------------------------------


def lock_wallet(s: Session, wallet_id: uuid.UUID, *, system: bool = False) -> Wallet:
    """Lock the wallet row. Owner actions need an active wallet; system steps (funding
    events, reversals, releasing or committing holds, refunds) must still run on a
    restricted wallet, or a restriction would strand money mid-flight."""
    wallet = s.get(Wallet, wallet_id, with_for_update=True, populate_existing=True)
    if wallet is None:
        raise TrollieError(ErrorCode.NOT_FOUND, "wallet not found")
    if wallet.status != "active" and not system:
        if wallet.status == "restricted":
            _require_active(wallet)
        raise TrollieError(ErrorCode.AUTHORITY_DENIED, "wallet is not active", status=wallet.status)
    return wallet


def wallet_for(s: Session, account_id: uuid.UUID) -> Wallet:
    wallet = s.scalars(select(Wallet).where(Wallet.account_id == account_id)).one_or_none()
    if wallet is None:
        raise TrollieError(ErrorCode.NOT_FOUND, "wallet not found")
    return wallet


def unallocated_acct(s: Session, wallet_id: uuid.UUID) -> uuid.UUID:
    return account(s, chart.CUSTOMER_UNALLOCATED, wallet_id)


def envelope_acct(s: Session, envelope_id: uuid.UUID) -> uuid.UUID:
    return account(s, chart.ENVELOPE_AVAILABLE, envelope_id)


def reserved_acct(s: Session, wallet_id: uuid.UUID) -> uuid.UUID:
    return account(s, chart.PURCHASE_RESERVED, wallet_id)


def _external(s: Session) -> uuid.UUID:
    return account(s, chart.SIM_EXTERNAL_FUNDS, None)


def balances(s: Session, wallet_id: uuid.UUID) -> dict[str, Any]:
    """What the wallet UI shows. Pending top-ups are listed but never counted as usable."""
    envelopes = {
        str(e.id): balance(s, envelope_acct(s, e.id))
        for e in s.scalars(select(Envelope).where(Envelope.wallet_id == wallet_id))
    }
    unallocated = balance(s, unallocated_acct(s, wallet_id))
    reserved = balance(s, reserved_acct(s, wallet_id))
    frozen = balance(s, account(s, chart.FROZEN_FUNDS, wallet_id))
    pending = s.scalar(
        select(func.coalesce(func.sum(FundingIntent.amount_minor), 0)).where(
            FundingIntent.wallet_id == wallet_id, FundingIntent.state.in_(["created", "pending"])
        )
    )
    return {
        "simulated": True,
        "label": "SIMULATED — NOT REAL MONEY",
        "currency": "ZAR",
        "unallocated_minor": unallocated,
        "envelopes_minor": envelopes,
        "reserved_minor": reserved,
        "frozen_minor": frozen,
        "pending_topups_minor": int(pending),
        "total_minor": unallocated + sum(envelopes.values()) + reserved + frozen,
    }


# --- W1: ownership and funding -------------------------------------------------------


def open_wallet(s: Session, *, account_id: uuid.UUID) -> Wallet:
    wallet = Wallet(account_id=account_id, funding_reference=f"TRL-{secrets.token_hex(5).upper()}")
    s.add(wallet)
    s.flush()
    audit(
        s,
        actor=f"account:{account_id}",
        action="wallet.open",
        object_type="wallet",
        object_id=wallet.id,
    )
    return wallet


def create_funding_intent(s: Session, *, wallet_id: uuid.UUID, amount_minor: int) -> FundingIntent:
    intent = FundingIntent(
        wallet_id=wallet_id, amount_minor=amount_minor, transfer_ref=f"tfr-{uuid.uuid4()}"
    )
    s.add(intent)
    s.flush()
    return intent


def apply_funding_event(s: Session, *, event_type: str, data: dict[str, Any], event_id: str) -> str:
    """Apply one verified provider funding event. Returns what happened."""
    transfer_ref = data.get("transfer_ref")
    intent = s.scalars(
        select(FundingIntent).where(FundingIntent.transfer_ref == transfer_ref).with_for_update()
    ).one_or_none()
    wallet = s.scalars(
        select(Wallet).where(Wallet.funding_reference == data.get("reference"))
    ).one_or_none()
    amount = data.get("amount_minor")
    if data.get("currency") != "ZAR" or data.get("destination_account") != COLLECTION_ACCOUNT:
        open_case(
            s,
            dedupe_key=f"funding-quarantine:{transfer_ref}:{event_id}",
            case_type="funding_quarantined",
            refs={
                "transfer_ref": transfer_ref,
                "currency": data.get("currency"),
                "destination": data.get("destination_account"),
            },
            difference_minor=amount if isinstance(amount, int) else None,
        )
        return "quarantined"  # W03: never guessed into a wallet
    if event_type == "funding.pending":
        if intent is not None and intent.state == "created":
            intent.state = "pending"
        return "pending"  # W02
    if event_type == "funding.failed":
        if intent is not None and intent.state in ("created", "pending"):
            intent.state = "failed"
        return "failed"
    if event_type == "funding.reversed":
        return reverse_funding(s, intent=intent, data=data)
    if event_type != "funding.confirmed":
        return "ignored"
    matched = (
        intent is not None
        and wallet is not None
        and intent.wallet_id == wallet.id
        and intent.amount_minor == amount
    )
    if not matched:
        # Confirmed receipt with unknown or mismatched ownership: suspense, not a wallet.
        post(
            s,
            posting_key=f"suspense:{transfer_ref}",
            event_type="funding_suspense",
            legs=[
                debit(_external(s), amount),
                credit(account(s, chart.UNMATCHED_SUSPENSE, None), amount),
            ],
        )
        open_case(
            s,
            dedupe_key=f"unmatched-funds:{transfer_ref}",
            case_type="unmatched_funds",
            refs={"transfer_ref": transfer_ref, "reference": data.get("reference")},
            difference_minor=amount,
        )
        return "suspense"
    lock_wallet(s, wallet.id, system=True)
    post(
        s,
        posting_key=f"topup:{transfer_ref}",
        event_type="wallet_topup",
        legs=[debit(_external(s), amount), credit(unallocated_acct(s, wallet.id), amount)],
    )
    intent.state = "confirmed"
    intent.evidence = {"event_id": event_id}
    return "credited"


def reverse_funding(s: Session, *, intent: FundingIntent | None, data: dict[str, Any]) -> str:
    """W13: a confirmed top-up is later reversed by the payer's bank. Freeze what remains,
    return it, and record any shortfall as a recovery receivable. History is never erased
    and no other customer's money is touched."""
    if intent is None or intent.state != "confirmed":
        return "ignored"
    wallet = lock_wallet(s, intent.wallet_id, system=True)
    amount = intent.amount_minor
    free = balance(s, unallocated_acct(s, wallet.id))
    frozen = account(s, chart.FROZEN_FUNDS, wallet.id)
    take = min(free, amount)
    if take:
        post(
            s,
            posting_key=f"freeze:{intent.transfer_ref}",
            event_type="wallet_freeze",
            legs=[debit(unallocated_acct(s, wallet.id), take), credit(frozen, take)],
        )
        post(
            s,
            posting_key=f"reversal-return:{intent.transfer_ref}",
            event_type="funding_reversal",
            legs=[debit(frozen, take), credit(_external(s), take)],
        )
    shortfall = amount - take
    if shortfall:
        post(
            s,
            posting_key=f"reversal-shortfall:{intent.transfer_ref}",
            event_type="funding_recovery",
            legs=[
                debit(account(s, chart.FUNDING_RECOVERY, wallet.id), shortfall),
                credit(_external(s), shortfall),
            ],
        )
        open_case(
            s,
            dedupe_key=f"recovery:{intent.transfer_ref}",
            case_type="funding_recovery",
            refs={"wallet_id": str(wallet.id), "transfer_ref": intent.transfer_ref},
            difference_minor=shortfall,
        )
    intent.state = "reversed"
    # A recalled payment usually means the money was not the payer's to send: restrict the
    # wallet until a person has reviewed it (I-047).
    if wallet.status == "active":
        wallet.status = "restricted"
        from app.controls.models import Incident

        s.add(
            Incident(
                kind="wallet_restricted",
                severity="high",
                details={"wallet_id": str(wallet.id), "transfer_ref": intent.transfer_ref,
                         "shortfall_minor": str(shortfall)},
            )
        )  # fmt: skip
    return "reversed"


# --- Allocation ----------------------------------------------------------------------


def allocate(
    s: Session,
    *,
    owner_account_id: uuid.UUID,
    envelope_id: uuid.UUID,
    amount_minor: int,
    business_key: str,
) -> None:
    """Owner moves unallocated funds into an envelope. Allocation never creates money."""
    envelope = _owned_envelope(s, owner_account_id, envelope_id)
    lock_wallet(s, envelope.wallet_id)
    if balance(s, unallocated_acct(s, envelope.wallet_id)) < amount_minor:
        raise TrollieError(ErrorCode.INSUFFICIENT_FUNDS, "not enough unallocated funds")
    post(
        s,
        posting_key=f"allocate:{business_key}",
        event_type="wallet_allocate",
        legs=[
            debit(unallocated_acct(s, envelope.wallet_id), amount_minor),
            credit(envelope_acct(s, envelope.id), amount_minor),
        ],
    )


def deallocate(
    s: Session,
    *,
    owner_account_id: uuid.UUID,
    envelope_id: uuid.UUID,
    amount_minor: int,
    business_key: str,
) -> None:
    envelope = _owned_envelope(s, owner_account_id, envelope_id)
    lock_wallet(s, envelope.wallet_id)
    if balance(s, envelope_acct(s, envelope.id)) < amount_minor:
        raise TrollieError(ErrorCode.INSUFFICIENT_FUNDS, "not enough funds in the envelope")
    post(
        s,
        posting_key=f"deallocate:{business_key}",
        event_type="wallet_deallocate",
        legs=[
            debit(envelope_acct(s, envelope.id), amount_minor),
            credit(unallocated_acct(s, envelope.wallet_id), amount_minor),
        ],
    )


def _owned_envelope(s: Session, owner_account_id: uuid.UUID, envelope_id: uuid.UUID) -> Envelope:
    envelope = s.get(Envelope, envelope_id)
    if envelope is None or s.get(Wallet, envelope.wallet_id).account_id != owner_account_id:
        raise TrollieError(ErrorCode.NOT_FOUND, "envelope not found")
    return envelope


def create_envelope(
    s: Session, *, owner_account_id: uuid.UUID, agent_id: uuid.UUID | None, label: str
) -> Envelope:
    wallet = wallet_for(s, owner_account_id)
    envelope = Envelope(wallet_id=wallet.id, agent_id=agent_id, label=label)
    s.add(envelope)
    s.flush()
    return envelope


# --- W2: purchases -------------------------------------------------------------------


def source_account(
    s: Session, wallet_id: uuid.UUID, funding_source: str
) -> tuple[uuid.UUID, uuid.UUID | None]:
    """Resolve `wallet:unallocated` or `wallet:envelope:<id>` (A4) to a ledger account."""
    parts = funding_source.split(":")
    if parts[:2] == ["wallet", "unallocated"]:
        return unallocated_acct(s, wallet_id), None
    if parts[:2] == ["wallet", "envelope"] and len(parts) == 3:
        envelope = s.get(Envelope, uuid.UUID(parts[2]))
        if envelope is None or envelope.wallet_id != wallet_id or envelope.status != "active":
            raise TrollieError(ErrorCode.AUTHORITY_DENIED, "envelope not usable")
        return envelope_acct(s, envelope.id), envelope.id
    raise TrollieError(ErrorCode.CAPABILITY_NOT_ENABLED, "unsupported wallet funding source")


def validate_funding_source(
    s: Session, account_id: uuid.UUID, funding_source: str, amount_minor: int
) -> None:
    """Advisory check when a quote is firmed; the binding check is at reservation."""
    wallet = wallet_for(s, account_id)
    acct, _ = source_account(s, wallet.id, funding_source)
    if balance(s, acct) < amount_minor:
        raise TrollieError(ErrorCode.INSUFFICIENT_FUNDS, "not enough available funds")


def clearing_minor(s: Session, wallet_id: uuid.UUID, now: datetime) -> int:
    """Top-ups confirmed less than the clearing period ago (I-047). A bank can still recall
    money for a while after confirming it; until then it is not treated as settled."""
    from app.config import get_settings
    from app.ledger.models import LedgerTransaction

    minutes = get_settings().wallet_clearing_minutes
    rows = s.execute(
        select(FundingIntent.amount_minor)
        .join(
            LedgerTransaction,
            LedgerTransaction.posting_key == "topup:" + FundingIntent.transfer_ref,
        )
        .where(
            FundingIntent.wallet_id == wallet_id,
            FundingIntent.state == "confirmed",
            LedgerTransaction.posted_at > now - timedelta(minutes=minutes),
        )
    ).all()
    return sum(r[0] for r in rows)


def _require_active(wallet: Wallet) -> None:
    if wallet.status != "active":
        raise TrollieError(
            ErrorCode.FUNDS_ON_HOLD,
            "this wallet is restricted while a recalled payment is reviewed",
            status=wallet.status,
        )


def spendable_now(s: Session, wallet_id: uuid.UUID, now: datetime) -> tuple[int, int]:
    """(money that may be spent now across the wallet, amount held back while clearing)."""
    from app.config import get_settings

    spendable = balance(s, unallocated_acct(s, wallet_id)) + sum(
        balance(s, envelope_acct(s, e.id))
        for e in s.scalars(select(Envelope).where(Envelope.wallet_id == wallet_id))
    )
    allowance = get_settings().wallet_clearing_allowance_minor
    held = max(0, clearing_minor(s, wallet_id, now) - allowance)
    return spendable - held, held


def reserve(
    s: Session,
    *,
    account_id: uuid.UUID,
    order_id: uuid.UUID,
    funding_source: str,
    amount_minor: int,
    now: datetime | None = None,
) -> WalletReservation:
    """Atomically hold funds for one purchase under the wallet lock (W05, W07)."""
    wallet = lock_wallet(s, wallet_for(s, account_id).id)
    _require_active(wallet)
    acct, envelope_id = source_account(s, wallet.id, funding_source)
    if balance(s, acct) < amount_minor:
        raise TrollieError(
            ErrorCode.INSUFFICIENT_FUNDS,
            "not enough available funds",
            funding_source=funding_source,
        )
    available, held = spendable_now(s, wallet.id, now or datetime.now(UTC))
    if available < amount_minor:
        raise TrollieError(
            ErrorCode.FUNDS_ON_HOLD,
            "part of your recent top-up is still clearing",
            spendable_now_minor=max(0, available),
            clearing_minor=held,
        )
    res = WalletReservation(
        wallet_id=wallet.id, envelope_id=envelope_id, order_id=order_id, amount_minor=amount_minor
    )
    s.add(res)
    s.flush()
    post(
        s,
        posting_key=f"wallet-reserve:{res.id}",
        event_type="wallet_reserve",
        legs=[debit(acct, amount_minor), credit(reserved_acct(s, wallet.id), amount_minor)],
    )
    return res


def _source_of(s: Session, res: WalletReservation) -> uuid.UUID:
    return (
        envelope_acct(s, res.envelope_id) if res.envelope_id else unallocated_acct(s, res.wallet_id)
    )


def release(s: Session, *, order_id: uuid.UUID) -> bool:
    """Return held funds to their source exactly once (W11). False if nothing to release."""
    res = s.scalars(
        select(WalletReservation).where(WalletReservation.order_id == order_id)
    ).one_or_none()
    if res is None:
        return False
    lock_wallet(s, res.wallet_id, system=True)
    s.refresh(res, with_for_update=True)
    if res.state != "held":
        return False
    post(
        s,
        posting_key=f"wallet-release:{res.id}",
        event_type="wallet_release",
        legs=[
            debit(reserved_acct(s, res.wallet_id), res.amount_minor),
            credit(_source_of(s, res), res.amount_minor),
        ],
    )
    res.state = "released"
    res.version += 1
    return True


def commit(s: Session, *, order_id: uuid.UUID, parties: list[dict]) -> int:
    """Turn held funds into obligations to the named recipients; release any remainder."""
    res = s.scalars(select(WalletReservation).where(WalletReservation.order_id == order_id)).one()
    lock_wallet(s, res.wallet_id, system=True)
    s.refresh(res, with_for_update=True)
    if res.state == "committed":
        return res.amount_minor
    if res.state != "held":
        raise TrollieError(ErrorCode.INVALID_STATE_TRANSITION, "reservation is not held")
    committed = sum(p["amount_minor"] for p in parties)
    if committed > res.amount_minor:
        raise TrollieError(ErrorCode.AUTHORITY_DENIED, "commitment exceeds reserved funds")
    reserved = reserved_acct(s, res.wallet_id)
    legs = [debit(reserved, committed)]
    legs += [
        credit(recipient_account(s, p), p["amount_minor"]) for p in parties if p["amount_minor"] > 0
    ]
    post(s, posting_key=f"wallet-commit:{res.id}", event_type="wallet_commit", legs=legs)
    remainder = res.amount_minor - committed
    if remainder:
        post(
            s,
            posting_key=f"wallet-commit-remainder:{res.id}",
            event_type="wallet_release",
            legs=[debit(reserved, remainder), credit(_source_of(s, res), remainder)],
        )
    res.state = "committed"
    res.amount_minor = committed
    res.version += 1
    return committed


def refund_to_wallet(
    s: Session, *, order_id: uuid.UUID, business_key: str, parties: list[dict], grant_active: bool
) -> WalletRefund:
    """A5: back to the envelope it came from while that envelope and its grant are active,
    otherwise to owner unallocated. Never exceeds what was committed (W12). Grant counters
    are not touched."""
    existing = s.scalars(
        select(WalletRefund).where(WalletRefund.business_key == business_key)
    ).one_or_none()
    amount = sum(p["amount_minor"] for p in parties)
    if existing is not None:
        if existing.amount_minor != amount:
            raise TrollieError(
                ErrorCode.DUPLICATE_OPERATION_CONFLICT, "refund key reused with a different amount"
            )
        return existing
    res = s.scalars(select(WalletReservation).where(WalletReservation.order_id == order_id)).one()
    lock_wallet(s, res.wallet_id, system=True)
    if res.state != "committed":
        raise TrollieError(ErrorCode.INVALID_STATE_TRANSITION, "nothing was committed")
    already = s.scalar(
        select(func.coalesce(func.sum(WalletRefund.amount_minor), 0)).where(
            WalletRefund.order_id == order_id
        )
    )
    if already + amount > res.amount_minor:
        raise TrollieError(
            ErrorCode.VALIDATION_FAILED,
            "refund exceeds the remaining refundable amount",
            refundable=res.amount_minor - int(already),
        )
    from app.orders.models import Order
    from app.orders.service import check_claim_caps

    check_claim_caps(s, s.get(Order, order_id), parties)  # serialised by the wallet lock
    envelope = s.get(Envelope, res.envelope_id) if res.envelope_id else None
    to_envelope = envelope is not None and envelope.status == "active" and grant_active
    destination_acct = (
        envelope_acct(s, envelope.id) if to_envelope else unallocated_acct(s, res.wallet_id)
    )
    refund = WalletRefund(
        order_id=order_id,
        business_key=business_key,
        amount_minor=amount,
        destination=f"envelope:{envelope.id}" if to_envelope else "unallocated",
        economic_allocation=[
            {
                k: p[k]
                for k in ("party_type", "party_id", "amount_minor", "leg_id", "line_id")
                if k in p
            }
            for p in parties
        ],
    )
    s.add(refund)
    s.flush()
    legs = [
        debit(recipient_account(s, p), p["amount_minor"]) for p in parties if p["amount_minor"] > 0
    ]
    legs.append(credit(destination_acct, amount))
    post(s, posting_key=f"wallet-refund:{refund.id}", event_type="wallet_refund", legs=legs)
    return refund


# --- Redemption ----------------------------------------------------------------------


def request_redemption(
    s: Session, *, owner_account_id: uuid.UUID, amount_minor: int, business_key: str, now: datetime
) -> Redemption:
    """Withdraw unallocated funds to the verified original source (simulated payout)."""
    wallet = lock_wallet(s, wallet_for(s, owner_account_id).id)
    existing = s.scalars(
        select(Redemption).where(Redemption.business_key == business_key)
    ).one_or_none()
    if existing is not None:
        return existing
    _require_active(wallet)
    if balance(s, unallocated_acct(s, wallet.id)) < amount_minor:
        raise TrollieError(ErrorCode.INSUFFICIENT_FUNDS, "not enough unallocated funds")
    clearing = clearing_minor(s, wallet.id, now)
    if balance(s, unallocated_acct(s, wallet.id)) - clearing < amount_minor:
        raise TrollieError(
            ErrorCode.FUNDS_ON_HOLD,
            "recent top-ups cannot be withdrawn until they clear",
            clearing_minor=clearing,
        )
    redemption = Redemption(
        wallet_id=wallet.id, business_key=business_key, amount_minor=amount_minor, state="approved"
    )
    s.add(redemption)
    s.flush()
    post(
        s,
        posting_key=f"redeem:{redemption.id}",
        event_type="wallet_redemption",
        legs=[
            debit(unallocated_acct(s, wallet.id), amount_minor),
            credit(account(s, chart.REDEMPTION_PAYABLE, wallet.id), amount_minor),
        ],
    )
    return redemption


def complete_redemption(s: Session, *, redemption_id: uuid.UUID) -> None:
    redemption = s.get(Redemption, redemption_id, with_for_update=True)
    if redemption.state != "approved":
        return
    post(
        s,
        posting_key=f"redeem-paid:{redemption.id}",
        event_type="wallet_redemption_paid",
        legs=[
            debit(
                account(s, chart.REDEMPTION_PAYABLE, redemption.wallet_id), redemption.amount_minor
            ),
            credit(_external(s), redemption.amount_minor),
        ],
    )
    redemption.state = "paid_simulated"

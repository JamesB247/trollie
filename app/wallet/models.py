"""Synthetic wallet records (DECISIONS.md D-W01-D-W03, A2-A5). SIMULATED — NOT REAL MONEY.

Balances are never stored here: they are derived from ledger accounts. These tables hold
ownership, permissions, intents and counters.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, created_at, uuid_pk


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_accounts.id"), unique=True)
    currency: Mapped[str] = mapped_column(Text, default="ZAR")
    # Every top-up carries this reference so inbound funds can be matched to their owner.
    funding_reference: Mapped[str] = mapped_column(Text, unique=True)
    status: Mapped[str] = mapped_column(Text, default="active")
    created_at: Mapped[datetime] = created_at()


class Agent(Base):
    """An agent identity acting for one account. Not a legal account holder (D-W01)."""

    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_accounts.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    # Set when the agent behaves like a stolen or broken agent; every call it makes is then
    # refused until the owner reviews it (I-046).
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspended_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()


class Envelope(Base):
    """An exclusive allocation of owner funds to one agent (first implementation, D-W01)."""

    __tablename__ = "wallet_envelopes"

    id: Mapped[uuid.UUID] = uuid_pk()
    wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"), index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agents.id"), unique=True)
    label: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="active")
    created_at: Mapped[datetime] = created_at()


class Grant(Base):
    """A versioned spending permission for one agent over one envelope.

    approval_mode `per_quote`: the agent may only propose; the owner approves each quote.
    approval_mode `mandate`: owner-approved (passkey) bounded authority to execute quotes that
    satisfy every condition below (A2). Only the owner can create or broaden a grant.
    """

    __tablename__ = "agent_grants"
    __table_args__ = (
        UniqueConstraint("agent_id", "version"),
        CheckConstraint("per_order_cap_minor > 0 AND period_cap_minor > 0", name="caps_positive"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"), index=True)
    envelope_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallet_envelopes.id"))
    version: Mapped[int]
    approval_mode: Mapped[str] = mapped_column(Text)
    merchant_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    product_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    categories: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    address_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("address_versions.id"))
    per_order_cap_minor: Mapped[int]
    period_cap_minor: Mapped[int]
    period_days: Mapped[int] = mapped_column(default=7)
    max_orders_per_day: Mapped[int] = mapped_column(default=3)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    purpose: Mapped[str] = mapped_column(Text)
    grant_hash: Mapped[str] = mapped_column(Text)
    # Mandate grants become active only after a passkey approval of exactly this hash.
    approval_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("approvals.id"))
    status: Mapped[str] = mapped_column(Text, default="pending_approval")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()


class GrantUsage(Base):
    """Authority counters. Refunds never reduce them (A5)."""

    __tablename__ = "grant_usage"

    id: Mapped[uuid.UUID] = uuid_pk()
    grant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_grants.id"), index=True)
    quote_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quotes.id"), unique=True)
    amount_minor: Mapped[int]
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FundingIntent(Base):
    __tablename__ = "funding_intents"
    __table_args__ = (CheckConstraint("amount_minor > 0", name="amount_positive"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"), index=True)
    amount_minor: Mapped[int]
    transfer_ref: Mapped[str] = mapped_column(Text, unique=True)
    state: Mapped[str] = mapped_column(Text, default="created")
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = created_at()


class WalletReservation(Base):
    """Funds held for one purchase. Released or committed exactly once."""

    __tablename__ = "wallet_reservations"
    __table_args__ = (CheckConstraint("amount_minor > 0", name="amount_positive"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"), index=True)
    envelope_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("wallet_envelopes.id"))
    order_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    amount_minor: Mapped[int]
    state: Mapped[str] = mapped_column(Text, default="held")
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = created_at()


class Redemption(Base):
    __tablename__ = "wallet_redemptions"
    __table_args__ = (CheckConstraint("amount_minor > 0", name="amount_positive"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"), index=True)
    business_key: Mapped[str] = mapped_column(Text, unique=True)
    amount_minor: Mapped[int]
    destination: Mapped[str] = mapped_column(Text, default="verified_original_source")
    state: Mapped[str] = mapped_column(Text, default="requested")
    created_at: Mapped[datetime] = created_at()


class MandateExecution(Base):
    """Authority record for one quote executed under a mandate, instead of a per-quote
    approval. One per quote."""

    __tablename__ = "mandate_executions"

    id: Mapped[uuid.UUID] = uuid_pk()
    grant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_grants.id"), index=True)
    quote_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quotes.id"), unique=True)
    quote_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()


class WalletRefund(Base):
    """Refund of a wallet-funded purchase back into the wallet (A5). One per business key."""

    __tablename__ = "wallet_refunds"
    __table_args__ = (CheckConstraint("amount_minor > 0", name="amount_positive"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(index=True)
    business_key: Mapped[str] = mapped_column(Text, unique=True)
    amount_minor: Mapped[int]
    destination: Mapped[str] = mapped_column(Text)  # envelope:<id> | unallocated
    economic_allocation: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at()

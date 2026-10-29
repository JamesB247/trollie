"""Request bodies. Every schema forbids unknown fields, so a caller (human or agent) cannot
smuggle a price, payee, address, URL or status into any request (blueprint §13.2; T45, T47)."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Upper bounds on caller-supplied numbers. Without them an absurd value (10**30 packs) reached
# the database and failed as a server error instead of a validation error (crowd simulation).
MAX_MINOR = 100_000_000  # R1 000 000 per amount in this sandbox
MAX_PACKS = 1_000
MAX_MEASURE = 1_000_000  # 1 000 kg / 1 000 l / 1 000 000 units


class SessionIn(Strict):
    address_version_id: uuid.UUID
    budget_minor: int | None = Field(default=None, gt=0, le=MAX_MINOR)
    deadline: datetime | None = None


class CandidateIn(Strict):
    product_id: uuid.UUID
    rank: int = Field(default=0, ge=0, le=100)
    max_unit_price_minor: int | None = Field(default=None, gt=0, le=MAX_MINOR)


class QuantityIn(Strict):
    packs: int | None = Field(default=None, gt=0, le=MAX_PACKS)
    measure: int | None = Field(default=None, gt=0, le=MAX_MEASURE)
    unit: Literal["ml", "g", "each"] | None = None


class ItemIn(Strict):
    line_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    rule: Literal["locked", "preferred", "flexible"] = "flexible"
    candidates: list[CandidateIn] = Field(min_length=1, max_length=10)
    quantity: QuantityIn
    must_have: bool = False
    needs_clarification: str | None = Field(default=None, max_length=500)


class EstimateIn(Strict):
    allow_omit_optional: bool = False


class FirmIn(Strict):
    # Asked clearly, never preselected (PRD partial-fulfilment rules): no default.
    fulfilment_mode: Literal["complete_required", "allow_partial"]
    permitted_omissions: list[str] = Field(default_factory=list)
    funding_source: str = Field(
        pattern=r"^(pay_per_order:(card_auth_capture|immediate)|"
        r"wallet:unallocated|wallet:envelope:[0-9a-f-]{36})$"
    )


class PurchaseRequestIn(Strict):
    quote_id: uuid.UUID
    note: str | None = Field(default=None, max_length=500)


class ChallengeIn(Strict):
    subject_type: Literal["quote", "mandate"]
    subject_id: uuid.UUID


class AssertionIn(Strict):
    challenge_id: uuid.UUID
    credential: dict[str, Any]


class OrderIn(Strict):
    approval_id: uuid.UUID


class IssueIn(Strict):
    leg_id: str = Field(max_length=64)
    # Every claim reason is about an item, so the claim names its quote line; a line can
    # never be refunded beyond its total (crowd simulation: repeat claims for one item).
    line_id: str = Field(min_length=1, max_length=64)
    amount_minor: int = Field(gt=0, le=MAX_MINOR)
    reason: Literal["missing_item", "damaged", "wrong_item"]


class AmountIn(Strict):
    amount_minor: int = Field(gt=0, le=MAX_MINOR)


class AgentIn(Strict):
    name: str = Field(min_length=1, max_length=80)


class GrantIn(Strict):
    approval_mode: Literal["per_quote", "mandate"]
    address_version_id: uuid.UUID
    per_order_cap_minor: int = Field(gt=0, le=MAX_MINOR)
    period_cap_minor: int = Field(gt=0, le=MAX_MINOR)
    period_days: int = Field(default=7, gt=0, le=31)
    max_orders_per_day: int = Field(default=3, gt=0, le=20)
    valid_days: int = Field(default=30, gt=0, le=90)
    merchant_ids: list[uuid.UUID] = Field(default_factory=list)
    product_ids: list[uuid.UUID] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    purpose: str = Field(default="household groceries", max_length=200)


class ExecuteIn(Strict):
    quote_id: uuid.UUID


class PreferenceIn(Strict):
    product_id: uuid.UUID | None = None
    category: str | None = None
    rule: Literal["locked", "preferred", "flexible"]

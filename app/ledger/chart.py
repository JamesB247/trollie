"""Synthetic operational subledger (DECISIONS.md D-S03.2).

This is a simulator chart, not a finance-approved statutory chart. Account classes
describe the control meaning inside the simulator; they do not establish legal
ownership of any funds.
"""

from dataclasses import dataclass

from app.ledger.models import AccountClass


@dataclass(frozen=True)
class AccountType:
    code: str
    owner_type: str
    account_class: AccountClass
    description: str


def _t(code: str, owner: str, cls: AccountClass, desc: str) -> AccountType:
    return AccountType(code, owner, cls, desc)


A, L, R, X, E = (
    AccountClass.ASSET,
    AccountClass.LIABILITY,
    AccountClass.REVENUE,
    AccountClass.EXPENSE,
    AccountClass.EQUITY,
)

# Wallet (W1-W3)
SIM_EXTERNAL_FUNDS = _t("sim_external_funds", "platform", A, "Funds confirmed by the simulator")
CUSTOMER_UNALLOCATED = _t("customer_unallocated", "wallet", L, "Owner funds not in an envelope")
ENVELOPE_AVAILABLE = _t("envelope_available", "envelope", L, "Exclusive delegated funds")
PURCHASE_RESERVED = _t("purchase_reserved", "wallet", L, "Held for a pending purchase")
REDEMPTION_PAYABLE = _t("redemption_payable", "wallet", L, "Reserved for approved redemption")
UNMATCHED_SUSPENSE = _t("unmatched_suspense", "platform", L, "Receipt with unknown ownership")
FROZEN_FUNDS = _t("frozen_funds", "wallet", L, "Disputed or reversed funding, not spendable")
FUNDING_RECOVERY = _t("funding_recovery_receivable", "wallet", A, "Owed back after a reversal")

# Recipients
MERCHANT_PAYABLE = _t("merchant_payable", "merchant", L, "Owed to a named seller")
COURIER_PAYABLE = _t("courier_payable", "courier", L, "Owed to a named courier")
PLATFORM_FEE_CLEARING = _t("platform_fee_clearing", "platform", L, "Fee awaiting recognition")
REFUND_RECOVERY = _t("refund_recovery_receivable", "merchant", A, "Recoverable from a merchant")

# Pay-per-order (provider-collected)
PROVIDER_CLEARING = _t("provider_clearing", "provider", A, "Captured by provider, not settled")
CUSTOMER_REFUND_PAYABLE = _t("customer_refund_payable", "account", L, "Refund owed to customer")
SETTLED_TO_RECIPIENTS = _t("settled_to_recipients", "provider", A, "Mirror of reported payouts")

# Platform
OPERATING_RESERVE = _t("operating_reserve", "platform", A, "Platform-funded reserve")
RESERVE_FUNDING = _t("operating_reserve_funding", "platform", E, "Platform equity for reserve")
PROVIDER_FEES = _t("provider_fees", "platform", X, "Simulated provider processing fees")
LOSSES = _t("losses", "platform", X, "Recognised losses after reconciliation")

ALL_TYPES = {t.code: t for t in globals().values() if isinstance(t, AccountType)}

"""Versioned provider capability profiles (blueprint §4.1; DECISIONS.md D-S03.7).

These profiles describe the *simulated* provider only. They are invented capabilities,
labelled as such; a live adapter can never inherit permission from them. Every use of
a capability goes through `require`, so unsupported combinations fail closed (T31).
"""

from dataclasses import dataclass
from datetime import timedelta

from app.errors import ErrorCode, TrollieError


@dataclass(frozen=True)
class CapabilityProfile:
    key: str
    version: int
    provider: str
    product: str
    method: str
    simulated: bool
    currency: str
    collection: str  # auth_capture | immediate
    capture_mode: str | None  # single_final | None
    max_additional_beneficiaries: int
    allocation_fixed_at: str  # authorisation | capture
    settlement_release_control: str  # provider_schedule | merchant_controlled
    partial_refunds: bool
    refund_allocation: str  # proportional | per_beneficiary
    status_lookup: bool
    idempotency_retention: timedelta
    webhook_signatures: bool
    settlement_reports: bool
    # Wallet-related fields (ADD §9.7). Invented for the simulator.
    stored_value_permitted: bool = False
    custodian_role: str | None = None
    funding_reversals: bool = False

    def require(self, capability: str, needed: object = True) -> None:
        value = getattr(self, capability)
        ok = (
            value >= needed
            if isinstance(needed, int) and not isinstance(needed, bool)
            else (value == needed)
        )
        if not ok:
            raise TrollieError(
                ErrorCode.CAPABILITY_NOT_ENABLED,
                f"{self.key} v{self.version} does not support {capability}={needed!r}",
                profile=self.key,
                capability=capability,
                available=str(value),
            )


_COMMON = dict(
    provider="simpay",
    simulated=True,
    currency="ZAR",
    settlement_release_control="provider_schedule",
    status_lookup=True,
    idempotency_retention=timedelta(hours=24),
    webhook_signatures=True,
    settlement_reports=True,
)

PROFILES = {
    p.key: p
    for p in (
        CapabilityProfile(
            key="simpay-card",
            allocation_fixed_at="capture",
            version=1,
            product="hosted-checkout",
            method="card",
            collection="auth_capture",
            capture_mode="single_final",
            max_additional_beneficiaries=4,
            partial_refunds=True,
            refund_allocation="proportional",
            **_COMMON,
        ),
        CapabilityProfile(
            key="simpay-instant",
            allocation_fixed_at="authorisation",
            version=1,
            product="pay-by-bank",
            method="instant_eft",
            collection="immediate",
            capture_mode=None,
            max_additional_beneficiaries=4,
            partial_refunds=True,
            refund_allocation="proportional",
            **_COMMON,
        ),
        # Deliberately restrictive: one destination, no partial refunds (T31).
        CapabilityProfile(
            key="simpay-restricted",
            allocation_fixed_at="authorisation",
            version=1,
            product="hosted-checkout",
            method="card",
            collection="auth_capture",
            capture_mode="single_final",
            max_additional_beneficiaries=1,
            partial_refunds=False,
            refund_allocation="proportional",
            **_COMMON,
        ),
        CapabilityProfile(
            key="simwallet",
            allocation_fixed_at="authorisation",
            version=1,
            product="stored-value-sandbox",
            method="wallet_topup",
            collection="immediate",
            capture_mode=None,
            max_additional_beneficiaries=4,
            partial_refunds=True,
            refund_allocation="per_beneficiary",
            stored_value_permitted=True,
            custodian_role="simulated_custodian",
            funding_reversals=True,
            **_COMMON,
        ),
    )
}

# Funding source → profile used for it in this build.
RAIL_PROFILES = {
    "pay_per_order:card_auth_capture": "simpay-card",
    "pay_per_order:immediate": "simpay-instant",
}


def profile_for(funding_source: str, override: str | None = None) -> CapabilityProfile:
    key = override or RAIL_PROFILES.get(funding_source)
    if key is None or key not in PROFILES:
        raise TrollieError(
            ErrorCode.CAPABILITY_NOT_ENABLED,
            "no capability profile for source",
            funding_source=funding_source,
        )
    return PROFILES[key]

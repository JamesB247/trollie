"""Runtime settings and startup guards.

This build has no live adapters. The guards make that impossible to forget:
- a live runtime refuses to start (no live adapters exist; DECISIONS.md D-S04, W20);
- the mandate fixture is honoured only under TROLLIE_ENV=test (DECISIONS.md A2).
"""

from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEV = "dev"
    TEST = "test"
    LIVE = "live"


class StartupRefused(RuntimeError):
    """Raised when configuration would let simulated components act as live ones."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TROLLIE_", env_file=".env", extra="ignore")

    env: Environment = Environment.DEV
    database_url: str = "postgresql+psycopg://trollie:trollie@localhost:5432/trollie"
    webauthn_rp_id: str = "localhost"
    webauthn_origin: str = "http://localhost:8000"
    address_key_file: str = "secrets/address_key"
    # Generated on first run, gitignored. Local development secrets only.
    session_secret_file: str = "secrets/session_secret"
    webhook_secret_file: str = "secrets/simpay_webhook_secret"
    mandate_fixture_enabled: bool = False
    # Run the job/webhook pump in a background thread (local development convenience).
    run_worker: bool = True
    # Trust controls (I-043..I-047). Crowd simulations compress these.
    delivery_grace_minutes: float = 30  # after the window, before a leg counts as overdue
    probation_exposure_cap_minor: int = 6_000_000  # undelivered value at a new merchant
    wallet_clearing_minutes: float = 4320  # new top-ups clear after this (72 h)
    wallet_clearing_allowance_minor: int = 150_000  # spendable from uncleared money
    agent_strike_limit: int = 3  # refused authority attempts before an agent is suspended
    agent_strike_window_minutes: float = 60
    agent_requests_per_window: int = 4  # purchase requests an agent may send per window
    merchant_circuit_failures: int = 3  # timeouts within the window that open the circuit
    merchant_circuit_window_s: float = 120
    merchant_circuit_open_s: float = 90


def check_startup(settings: Settings) -> None:
    if settings.env is Environment.LIVE:
        # TODO(blueprint §4.1, §20.4): live adapters require an approved capability
        # profile and the release evidence checklist. None exist in this build.
        raise StartupRefused(
            "live runtime is not supported: this build has simulated adapters only"
        )
    if settings.mandate_fixture_enabled and settings.env is not Environment.TEST:
        raise StartupRefused("mandate fixture may only be enabled when TROLLIE_ENV=test")


@lru_cache
def get_settings() -> Settings:
    return Settings()

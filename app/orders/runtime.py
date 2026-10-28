"""The set of collaborators an order needs. Built once at startup, or per test."""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session, sessionmaker

from app.clock import Clock
from app.merchants.adapter import MerchantAdapter
from app.payments.adapter import PaymentAdapter
from app.payments.operations import Executor


@dataclass
class Runtime:
    sessions: sessionmaker[Session]
    clock: Clock
    merchant: MerchantAdapter
    payments: PaymentAdapter
    courier: object
    webhook_secret: bytes
    environment: str
    provider_account: str = "sim-acct-1"
    # Test-only override to exercise a restrictive capability profile (T31).
    profile_override: str | None = None
    # DECISIONS.md A2: only honoured when the settings allow it (TROLLIE_ENV=test).
    mandate_fixture_enabled: bool = False
    # Dev harness: lets a demo pause the background pump while it arms simulator faults.
    worker_paused: bool = False
    executor: Executor = field(init=False)

    def __post_init__(self) -> None:
        self.executor = Executor(self.sessions, self.payments, self.clock)

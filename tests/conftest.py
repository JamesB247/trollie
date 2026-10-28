"""Test fixtures: a fresh, migrated test database per session.

Set TROLLIE_TEST_DATABASE_URL to point elsewhere; it must be a disposable database.
"""

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.config import Config
from hypothesis import settings as hypothesis_settings
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

import app.all_models  # noqa: F401
from app.clock import FixedClock
from app.config import Environment, Settings
from app.registry import register_all
from app.seed import seed
from app.simulators.merchant import SimulatedMerchant

TEST_DATABASE_URL = os.environ.get(
    "TROLLIE_TEST_DATABASE_URL",
    "postgresql+psycopg://trollie:trollie@localhost:5432/trollie_test",
)


def migrate(url: str, environment: str) -> None:
    cfg = Config("alembic.ini")
    cfg.attributes["database_url"] = url
    cfg.attributes["environment"] = environment
    command.upgrade(cfg, "head")


def reset_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings(env=Environment.TEST, database_url=TEST_DATABASE_URL, run_worker=False)


@pytest.fixture(scope="session")
def engine(test_settings: Settings) -> Iterator[Engine]:
    register_all()
    engine = create_engine(test_settings.database_url)
    reset_schema(engine)
    migrate(test_settings.database_url, Environment.TEST.value)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """A session on the shared test database. Tests use fresh UUID owners for isolation,
    because the ledger is append-only and cannot be cleaned between tests."""
    with Session(engine) as session:
        yield session


T0 = datetime(2026, 11, 2, 8, 0, tzinfo=UTC)


@pytest.fixture(scope="session")
def catalogue(engine: Engine) -> dict[str, uuid.UUID]:
    """The synthetic seed, created once at T0 for the whole test session."""
    with Session(engine) as session, session.begin():
        return seed(session, now=T0)


# HYPOTHESIS_PROFILE=thorough runs the property tests far longer (used before releases).
hypothesis_settings.register_profile("default", max_examples=300)
hypothesis_settings.register_profile("thorough", max_examples=5000)
hypothesis_settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "default"))


@pytest.fixture
def sessions(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def clock() -> "FixedClock":
    return FixedClock(T0)


@pytest.fixture
def merchant(engine: Engine, clock) -> "SimulatedMerchant":
    return SimulatedMerchant(engine, clock)


WEBHOOK_SECRET = b"test-simpay-webhook-secret"


@pytest.fixture(scope="session")
def split_world(engine: Engine) -> dict[str, uuid.UUID]:
    from tests.order_support import seed_split_world

    with Session(engine) as session, session.begin():
        return seed_split_world(session, now=T0)


@pytest.fixture
def rt(engine: Engine, clock):
    from app.orders.runtime import Runtime
    from app.simulators.courier import SimulatedCourier
    from app.simulators.payments import SimulatedPaymentProvider

    return Runtime(
        sessions=sessionmaker(engine, expire_on_commit=False),
        clock=clock,
        merchant=SimulatedMerchant(engine, clock),
        payments=SimulatedPaymentProvider(engine, clock, secret=WEBHOOK_SECRET, environment="test"),
        courier=SimulatedCourier(engine, clock),
        webhook_secret=WEBHOOK_SECRET,
        environment="test",
    )


@pytest.fixture(autouse=True)
def _clear_injected_faults(request):
    """Faults are per-test; one test's unconsumed fault must not leak into the next."""
    yield
    if "engine" in request.fixturenames:
        engine = request.getfixturevalue("engine")
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM sim_faults"))


@pytest.fixture(autouse=True)
def _kill_switch_must_not_leak(request):
    """A test that leaves the financial kill switch engaged fails here, not in later tests."""
    yield
    if "engine" not in request.fixturenames:
        return
    engine = request.getfixturevalue("engine")
    with engine.begin() as conn:
        engaged = (
            conn.execute(text("SELECT scope FROM kill_switches WHERE engaged")).scalars().all()
        )
        if engaged:
            conn.execute(text("UPDATE kill_switches SET engaged = false, reason = 'test reset'"))
    if engaged:
        pytest.fail(f"kill switch left engaged: {engaged}")

"""Test fixtures: a fresh, migrated test database per session.

Set TROLLIE_TEST_DATABASE_URL to point elsewhere; it must be a disposable database.
"""

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

import app.all_models  # noqa: F401
from app.config import Environment, Settings

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
    return Settings(env=Environment.TEST, database_url=TEST_DATABASE_URL)


@pytest.fixture(scope="session")
def engine(test_settings: Settings) -> Iterator[Engine]:
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

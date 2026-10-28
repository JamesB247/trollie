"""Database engine, sessions and the deployment marker check (W20)."""

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import Environment, Settings, StartupRefused


def make_engine(settings: Settings) -> Engine:
    return create_engine(settings.database_url, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def check_deployment_marker(engine: Engine, settings: Settings) -> None:
    """Refuse to run against a database whose marker disagrees with the runtime.

    A synthetic database must never be served by a live runtime, so simulated
    balances can never be presented as real value.
    """
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT environment, synthetic FROM deployment_marker")
        ).one_or_none()
    if row is None:
        raise StartupRefused("database has no deployment marker; run migrations")
    environment, synthetic = row
    if synthetic and settings.env is Environment.LIVE:
        raise StartupRefused("synthetic database cannot be used by a live runtime")
    if environment != settings.env.value:
        raise StartupRefused(
            f"database marker is {environment!r} but runtime is {settings.env.value!r}"
        )

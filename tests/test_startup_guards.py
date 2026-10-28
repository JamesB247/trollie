"""Startup guards: DECISIONS.md A2 (mandate fixture) and W20 (synthetic DB vs live runtime)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from app.config import Environment, Settings, StartupRefused, check_startup
from app.db import check_deployment_marker
from app.main import create_app


def test_live_runtime_refused():
    with pytest.raises(StartupRefused, match="live runtime"):
        check_startup(Settings(env=Environment.LIVE))


@pytest.mark.parametrize("env", [Environment.DEV, Environment.LIVE])
def test_mandate_fixture_refused_outside_test(env):
    with pytest.raises(StartupRefused):
        check_startup(Settings(env=env, mandate_fixture_enabled=True))


def test_mandate_fixture_allowed_in_test():
    check_startup(Settings(env=Environment.TEST, mandate_fixture_enabled=True))


def test_w20_synthetic_database_refused_under_live_runtime(engine: Engine):
    # check_startup would already refuse; this proves the database marker refuses independently.
    with pytest.raises(StartupRefused, match="synthetic database"):
        check_deployment_marker(engine, Settings(env=Environment.LIVE))


def test_marker_environment_mismatch_refused(engine: Engine):
    with pytest.raises(StartupRefused, match="marker is 'test'"):
        check_deployment_marker(engine, Settings(env=Environment.DEV))


def test_marker_is_single_row(engine: Engine):
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            text("INSERT INTO deployment_marker (environment, synthetic) VALUES ('dev', true)")
        )


def test_healthz_reports_simulated_money(engine: Engine, test_settings: Settings):
    with TestClient(create_app(test_settings)) as client:
        body = client.get("/healthz").json()
    assert body == {"status": "ok", "environment": "test", "simulated_money": True}

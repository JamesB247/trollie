"""Browser test of the approval page with a virtual authenticator (T22 passed_browser; DoD).

Starts the real server against a fresh database and drives Chromium through passkey setup,
approval, order placement and the simulated payment step. Skipped when Node Playwright is
not installed.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid

import httpx
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.approvals.models import Approval
from app.orders.models import Order
from tests.conftest import TEST_DATABASE_URL, migrate, reset_schema

E2E_DB = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/trollie_e2e"


def _playwright_available() -> bool:
    if shutil.which("node") is None:
        return False
    probe = subprocess.run(["node", "-e", "require('playwright')"], capture_output=True)
    return probe.returncode == 0


pytestmark = pytest.mark.skipif(
    not _playwright_available(), reason="Node Playwright is not installed"
)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    admin = create_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        if not conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'trollie_e2e'")
        ).first():
            conn.execute(text("CREATE DATABASE trollie_e2e"))
    admin.dispose()
    engine = create_engine(E2E_DB)
    reset_schema(engine)
    migrate(E2E_DB, "test")
    port = _free_port()
    env = {
        **os.environ,
        "TROLLIE_ENV": "test",
        "TROLLIE_DATABASE_URL": E2E_DB,
        "TROLLIE_RUN_WORKER": "false",
        "TROLLIE_WEBAUTHN_RP_ID": "localhost",
        "TROLLIE_WEBAUTHN_ORIGIN": f"http://localhost:{port}",
    }
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    base = f"http://localhost:{port}"
    for _ in range(100):
        try:
            if httpx.get(f"{base}/healthz", timeout=0.5).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    else:
        proc.kill()
        raise RuntimeError(proc.stdout.read().decode())
    yield base, engine
    proc.terminate()
    proc.wait(timeout=10)
    engine.dispose()


def test_approval_page_with_virtual_passkey(server):
    base, engine = server
    api = httpx.Client(base_url=base, timeout=10)
    api.post("/v1/dev/seed").raise_for_status()
    account = api.post("/v1/dev/accounts", json={"zone": "zone-a"}).json()
    h = {"Authorization": f"Bearer {account['token']}"}
    products = {
        p["name"] + p["variant"]: p["product_id"]
        for p in api.get("/v1/catalogue/products", headers=h).json()
    }
    sid = api.post(
        "/v1/shopping-sessions",
        headers=h,
        json={"address_version_id": account["address_version_id"]},
    ).json()["session_id"]
    for line, key in (("milk", "UHT milkfull cream"), ("tea", "Rooibos tea100 bags")):
        api.post(
            f"/v1/shopping-sessions/{sid}/items",
            headers=h,
            json={
                "line_id": line,
                "candidates": [{"product_id": products[key]}],
                "quantity": {"packs": 1},
            },
        ).raise_for_status()
    est = api.post(f"/v1/shopping-sessions/{sid}/quotes", headers=h, json={}).json()
    firm = api.post(
        f"/v1/quotes/{est['options']['cheapest']['quote_id']}/firm",
        headers=h,
        json={
            "fulfilment_mode": "complete_required",
            "funding_source": "pay_per_order:card_auth_capture",
        },
    ).json()

    run = subprocess.run(
        ["node", "tests/browser/approve.mjs"],
        capture_output=True,
        text=True,
        timeout=120,
        env={
            **os.environ,
            "BASE_URL": base,
            "TOKEN": account["token"],
            "QUOTE_ID": firm["quote_id"],
            "SCREENSHOT": os.environ.get("TROLLIE_SCREENSHOT", ""),
        },
    )
    result = json.loads(run.stdout.strip().splitlines()[-1])
    assert result["ok"], result
    page_text = result["approvalPageText"]
    assert "SIMULATED" in page_text and "Maximum total" in page_text
    assert "(Fictional)" in page_text and "Complete basket required" in page_text
    assert "Order FULFILLING" in result["heading"]

    with Session(engine) as s:
        approval = s.scalars(
            select(Approval).where(Approval.subject_id == uuid.UUID(firm["quote_id"]))
        ).one()
        assert approval.user_verified and approval.subject_hash == firm["quote_hash"]
        order = s.scalars(select(Order).where(Order.approval_id == approval.id)).one()
        assert order.state == "FULFILLING"

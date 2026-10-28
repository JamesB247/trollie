"""Build the FastAPI app and its runtime. All external parties are simulators."""

import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.accounts.crypto import AddressCipher
from app.api import dev_routes, pages, routes, wallet_routes
from app.api.deps import AppContext
from app.approvals.service import WebAuthnConfig
from app.clock import SystemClock
from app.config import Environment, Settings, check_startup, get_settings
from app.db import check_deployment_marker, make_engine, make_session_factory
from app.errors import TrollieError
from app.orders.handlers import pump
from app.orders.runtime import Runtime
from app.redaction import install_log_redaction
from app.registry import register_all
from app.secrets_store import load_or_create
from app.simulators.courier import SimulatedCourier
from app.simulators.merchant import SimulatedMerchant
from app.simulators.payments import SimulatedPaymentProvider

log = logging.getLogger(__name__)


@lru_cache
def address_cipher() -> AddressCipher:
    return AddressCipher.from_file(get_settings().address_key_file)


def build_runtime(settings: Settings, engine) -> Runtime:
    clock = SystemClock()
    secret = load_or_create(settings.webhook_secret_file)
    return Runtime(
        sessions=make_session_factory(engine),
        clock=clock,
        merchant=SimulatedMerchant(engine, clock),
        payments=SimulatedPaymentProvider(
            engine, clock, secret=secret, environment=settings.env.value
        ),
        courier=SimulatedCourier(engine, clock),
        webhook_secret=secret,
        environment=settings.env.value,
        mandate_fixture_enabled=settings.mandate_fixture_enabled
        and settings.env is Environment.TEST,
    )


def _worker(rt: Runtime, stop: threading.Event) -> None:
    while not stop.wait(1.0):
        try:
            pump(rt, rt.payments)
        except Exception:  # noqa: BLE001 - keep the dev worker alive
            log.exception("background pump failed")


def create_app(settings: Settings | None = None, runtime: Runtime | None = None) -> FastAPI:
    settings = settings or get_settings()
    check_startup(settings)
    register_all()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        install_log_redaction()
        engine = make_engine(settings)
        check_deployment_marker(engine, settings)
        rt = runtime or build_runtime(settings, engine)
        app.state.ctx = AppContext(
            rt=rt,
            webauthn=WebAuthnConfig(rp_id=settings.webauthn_rp_id, origin=settings.webauthn_origin),
            session_secret=load_or_create(settings.session_secret_file),
            dev_tools=settings.env in (Environment.DEV, Environment.TEST),
        )
        stop = threading.Event()
        thread = None
        if settings.run_worker and runtime is None:
            thread = threading.Thread(target=_worker, args=(rt, stop), daemon=True)
            thread.start()
        yield
        stop.set()
        if thread:
            thread.join(timeout=5)
        engine.dispose()

    app = FastAPI(title="Trollie (simulated)", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings

    @app.exception_handler(TrollieError)
    async def trollie_error(request: Request, exc: TrollieError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": {k: str(v) for k, v in exc.details.items()},
            },
        )

    @app.get("/healthz")
    def healthz() -> dict[str, object]:
        return {"status": "ok", "environment": settings.env.value, "simulated_money": True}

    for module in (routes, wallet_routes, dev_routes, pages):
        app.include_router(module.router)
    return app

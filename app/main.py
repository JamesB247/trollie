"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, check_startup, get_settings
from app.db import check_deployment_marker, make_engine, make_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    check_startup(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_engine(settings)
        check_deployment_marker(engine, settings)
        app.state.engine = engine
        app.state.sessions = make_session_factory(engine)
        yield
        engine.dispose()

    app = FastAPI(title="Trollie (simulated)", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings

    @app.get("/healthz")
    def healthz() -> dict[str, object]:
        return {"status": "ok", "environment": settings.env.value, "simulated_money": True}

    return app

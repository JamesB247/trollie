"""ASGI entry point: `uvicorn app.main:create_app --factory`."""

from app.api.app_factory import create_app

__all__ = ["create_app"]

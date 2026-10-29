"""Request-scoped dependencies: the runtime, the caller, and authority checks."""

from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.api.auth import Principal, token_from, verify
from app.approvals.service import WebAuthnConfig
from app.errors import ErrorCode, TrollieError
from app.orders.runtime import Runtime


@dataclass
class AppContext:
    rt: Runtime
    webauthn: WebAuthnConfig
    session_secret: bytes
    dev_tools: bool


def ctx(request: Request) -> AppContext:
    return request.app.state.ctx


def db(c: AppContext = Depends(ctx)) -> Iterator[Session]:
    with c.rt.sessions() as session:
        yield session


def principal(request: Request, c: AppContext = Depends(ctx)) -> Principal:
    p = verify(c.session_secret, token_from(request))
    request.state.principal = p
    if p.kind == "agent":
        from app.wallet.agent_guard import ensure_active

        with c.rt.sessions() as s:
            ensure_active(s, p.agent_id)
    return p


def customer(p: Principal = Depends(principal)) -> Principal:
    """Endpoints that carry the owner's authority. Agents are refused (blueprint §13.2)."""
    if p.kind != "customer":
        raise TrollieError(ErrorCode.AUTHORITY_DENIED, "this action requires the account owner")
    return p


def dev_only(c: AppContext = Depends(ctx)) -> AppContext:
    if not c.dev_tools:
        raise TrollieError(ErrorCode.NOT_FOUND, "not found")
    return c

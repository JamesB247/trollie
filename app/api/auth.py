"""Development session tokens. NOT a production authentication system.

A token is `<kind>:<id>.<hmac>` signed with a generated local secret. It identifies either a
customer account or an agent acting for one. Real account security and recovery are out of
scope for this sprint; nothing here recovers an account from a phone number (T23).
"""

import hmac
import uuid
from dataclasses import dataclass

from fastapi import Request

from app.errors import ErrorCode, TrollieError

COOKIE = "trollie_session"


@dataclass(frozen=True)
class Principal:
    kind: str  # customer | agent
    account_id: uuid.UUID
    agent_id: uuid.UUID | None = None

    @property
    def actor(self) -> str:
        return f"agent:{self.agent_id}" if self.agent_id else f"account:{self.account_id}"


def _sig(secret: bytes, body: str) -> str:
    return hmac.new(secret, body.encode(), "sha256").hexdigest()


def issue(secret: bytes, principal: Principal) -> str:
    if principal.kind == "agent":
        body = f"agent:{principal.agent_id}:{principal.account_id}"
    else:
        body = f"customer:{principal.account_id}"
    return f"{body}.{_sig(secret, body)}"


def verify(secret: bytes, token: str | None) -> Principal:
    if not token or "." not in token:
        raise TrollieError(ErrorCode.AUTHORITY_DENIED, "authentication required")
    body, sig = token.rsplit(".", 1)
    if not hmac.compare_digest(_sig(secret, body), sig):
        raise TrollieError(ErrorCode.AUTHORITY_DENIED, "invalid session")
    parts = body.split(":")
    try:
        if parts[0] == "customer" and len(parts) == 2:
            return Principal("customer", uuid.UUID(parts[1]))
        if parts[0] == "agent" and len(parts) == 3:
            return Principal("agent", uuid.UUID(parts[2]), uuid.UUID(parts[1]))
    except ValueError:
        pass
    raise TrollieError(ErrorCode.AUTHORITY_DENIED, "invalid session")


def token_from(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.cookies.get(COOKIE)

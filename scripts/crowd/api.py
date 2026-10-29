"""HTTP plumbing and the shared event log."""

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx

# Verdicts recorded for every action.
OK = "ok"  # did what the actor wanted, and that was allowed
REFUSED = "refused"  # an attack or invalid action was correctly refused
FRICTION = "friction"  # an honest actor was blocked (may be correct, may be a product gap)
BREACH = "BREACH"  # an attack or rule violation succeeded
BUG = "BUG"  # server error or contract violation
SLOW = "SLOW"  # request exceeded the latency budget
INFO = "info"


@dataclass
class Event:
    t: float
    user: str
    archetype: str
    brain: str
    said: str
    action: str
    status: int | None
    code: str | None
    verdict: str
    detail: str
    ms: int


@dataclass
class Log:
    started: float = field(default_factory=time.monotonic)
    events: list[Event] = field(default_factory=list)

    def add(self, **kw: Any) -> Event:
        ev = Event(t=round(time.monotonic() - self.started, 2), **kw)
        self.events.append(ev)
        return ev

    def dump(self, path) -> None:
        with open(path, "w") as f:
            for ev in self.events:
                f.write(json.dumps(asdict(ev)) + "\n")


@dataclass
class Reply:
    status: int | None
    body: Any
    ms: int
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 300

    @property
    def code(self) -> str | None:
        if isinstance(self.body, dict):
            return self.body.get("code") or (
                "VALIDATION" if self.status == 422 and "detail" in self.body else None
            )
        return None


class Api:
    def __init__(self, base: str, timeout: float = 30.0) -> None:
        self.base = base
        self.http = httpx.AsyncClient(
            base_url=base, timeout=timeout, limits=httpx.Limits(max_connections=200)
        )

    async def close(self) -> None:
        await self.http.aclose()

    async def call(
        self,
        method: str,
        url: str,
        token: str | None = None,
        *,
        idem: str | bool | None = None,
        **kw: Any,
    ) -> Reply:
        headers = kw.pop("headers", {})
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if idem is True:
            idem = str(uuid.uuid4())
        if idem:
            headers["Idempotency-Key"] = idem
        t0 = time.monotonic()
        try:
            r = await self.http.request(method, url, headers=headers, **kw)
        except httpx.HTTPError as exc:
            return Reply(None, None, int((time.monotonic() - t0) * 1000), type(exc).__name__)
        ms = int((time.monotonic() - t0) * 1000)
        try:
            body = r.json()
        except ValueError:
            body = r.text[:500]
        return Reply(r.status_code, body, ms)

    async def must(self, method: str, url: str, token: str | None = None, **kw: Any) -> Any:
        r = await self.call(method, url, token, **kw)
        if not r.ok:
            raise RuntimeError(f"{method} {url} -> {r.status}: {r.body}")
        return r.body

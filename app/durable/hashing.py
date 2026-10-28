"""Canonical JSON and hashing shared by idempotency, quotes, approvals and the inbox."""

import hashlib
import json
import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any


def _default(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("naive datetimes cannot be canonicalised")
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, float):
        raise ValueError("floats are not allowed in canonical payloads")
    raise TypeError(f"cannot canonicalise {type(value).__name__}")


def _reject_floats(value: Any) -> None:
    if isinstance(value, float):
        raise ValueError("floats are not allowed in canonical payloads")
    if isinstance(value, dict):
        for v in value.values():
            _reject_floats(v)
    elif isinstance(value, list | tuple):
        for v in value:
            _reject_floats(v)


def canonical_json(value: Any) -> str:
    """Sorted keys, no whitespace, UTC ISO timestamps, no floats (money is integer cents)."""
    _reject_floats(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=_default)


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_hex(canonical_json(value))

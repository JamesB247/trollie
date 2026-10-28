"""Redaction of card numbers, security codes and SA ID numbers from logs and audit records.

None of these should exist in this build; redaction is defence in depth (CLAUDE.md rules).
"""

import logging
import re
from typing import Any

REDACTED = "[REDACTED]"

# 13-19 digits, optionally separated by single spaces or dashes: card PANs and 13-digit SA IDs.
_LONG_NUMBER = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_SENSITIVE_KEYS = re.compile(
    r"(pan|card.?number|cvv|cvc|security.?code|id.?number|identity.?number|password|secret|pin)$",
    re.IGNORECASE,
)


def redact_text(value: str) -> str:
    return _LONG_NUMBER.sub(REDACTED, value)


def redact(value: Any, key: str | None = None) -> Any:
    if key is not None and _SENSITIVE_KEYS.search(key):
        return REDACTED
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {k: redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [redact(v) for v in value]
    return value


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(str(record.msg))
        if record.args:
            record.args = tuple(redact(a) for a in record.args)
        return True


def install_log_redaction() -> None:
    for handler in logging.getLogger().handlers:
        handler.addFilter(RedactingFilter())

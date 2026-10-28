"""Redaction of card numbers, security codes and SA ID numbers from logs and audit records.

None of these should exist in this build; redaction is defence in depth (CLAUDE.md rules).
"""

import logging
import re
from typing import Any

REDACTED = "[REDACTED]"

# 13-19 digits, optionally separated by single spaces or dashes: card PANs and 13-digit SA IDs.
# Not adjacent to letters or digits, so digit runs inside hashes are left alone.
_LONG_NUMBER = re.compile(r"(?<![0-9A-Za-z])(?:\d[ -]?){12,18}\d(?![0-9A-Za-z])")
# Identifiers must survive redaction intact; UUID groups joined by dashes look like long numbers.
_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_SENSITIVE_KEYS = re.compile(
    r"(pan|card.?number|cvv|cvc|security.?code|id.?number|identity.?number|password|secret|pin)$",
    re.IGNORECASE,
)


def redact_text(value: str) -> str:
    parts: list[str] = []
    last = 0
    for match in _UUID.finditer(value):
        parts.append(_LONG_NUMBER.sub(REDACTED, value[last : match.start()]))
        parts.append(match.group())
        last = match.end()
    parts.append(_LONG_NUMBER.sub(REDACTED, value[last:]))
    return "".join(parts)


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

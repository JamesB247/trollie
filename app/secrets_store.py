"""Local secret files: created once with owner-only permissions, never committed."""

import os
import secrets
from pathlib import Path


def load_or_create(path: str | Path, *, nbytes: int = 32) -> bytes:
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return bytes.fromhex(path.read_text().strip())
        with os.fdopen(fd, "w") as fh:
            fh.write(secrets.token_hex(nbytes))
    return bytes.fromhex(path.read_text().strip())

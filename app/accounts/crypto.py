"""Address encryption provider (DECISIONS.md D-S03.5).

AES-256-GCM from the maintained `cryptography` library, a fresh random 96-bit nonce
per encryption, and the owner and address-version id as associated data, so a
ciphertext moved to another account or version fails to decrypt. Local keys only;
this is not equivalent to production KMS custody.
"""

import os
import secrets
import uuid
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class AddressCipher:
    def __init__(self, keys: dict[str, bytes], active_key_id: str) -> None:
        if active_key_id not in keys:
            raise ValueError("active key id not in key ring")
        for key in keys.values():
            if len(key) != 32:
                raise ValueError("address keys must be 256-bit")
        self._keys = keys
        self.active_key_id = active_key_id

    @classmethod
    def from_file(cls, path: str | Path) -> "AddressCipher":
        """Load (or, in development, create) a key file of `key_id:hexkey` lines."""
        path = Path(path)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as fh:
                fh.write(f"dev-1:{secrets.token_hex(32)}\n")
        keys: dict[str, bytes] = {}
        for line in path.read_text().splitlines():
            if line.strip():
                key_id, hexkey = line.strip().split(":", 1)
                keys[key_id] = bytes.fromhex(hexkey)
        return cls(keys, active_key_id=list(keys)[-1])

    @classmethod
    def ephemeral(cls) -> "AddressCipher":
        return cls({"ephemeral": AESGCM.generate_key(bit_length=256)}, "ephemeral")

    @staticmethod
    def _aad(account_id: uuid.UUID, address_version_id: uuid.UUID) -> bytes:
        return f"address:{account_id}:{address_version_id}".encode()

    def encrypt(
        self, plaintext: str, *, account_id: uuid.UUID, address_version_id: uuid.UUID
    ) -> tuple[str, bytes, bytes]:
        nonce = os.urandom(12)
        ciphertext = AESGCM(self._keys[self.active_key_id]).encrypt(
            nonce, plaintext.encode(), self._aad(account_id, address_version_id)
        )
        return self.active_key_id, nonce, ciphertext

    def decrypt(
        self,
        *,
        key_id: str,
        nonce: bytes,
        ciphertext: bytes,
        account_id: uuid.UUID,
        address_version_id: uuid.UUID,
    ) -> str:
        if key_id not in self._keys:
            raise ValueError(f"unknown address key version {key_id!r}")
        return (
            AESGCM(self._keys[key_id])
            .decrypt(nonce, ciphertext, self._aad(account_id, address_version_id))
            .decode()
        )

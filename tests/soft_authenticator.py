"""A software WebAuthn authenticator (ES256, 'none' attestation) for automated tests.

It produces real registration and assertion structures that the server verifies with
py_webauthn. It proves protocol behaviour only; it is not evidence that a person
completed PIN or biometric verification on a physical device (T22 stays manual_pending
for real devices).
"""

import base64
import hashlib
import json
import os
import struct

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from webauthn.helpers import encode_cbor

FLAG_UP, FLAG_UV, FLAG_AT = 0x01, 0x04, 0x40


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class SoftAuthenticator:
    def __init__(self, *, user_verifying: bool = True) -> None:
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.credential_id = os.urandom(32)
        self.sign_count = 0
        self.user_verifying = user_verifying

    def _cose_key(self) -> bytes:
        numbers = self.key.public_key().public_numbers()
        return encode_cbor(
            {
                1: 2,
                3: -7,
                -1: 1,
                -2: numbers.x.to_bytes(32, "big"),
                -3: numbers.y.to_bytes(32, "big"),
            }
        )

    def _flags(self, extra: int = 0) -> int:
        return FLAG_UP | (FLAG_UV if self.user_verifying else 0) | extra

    def register(self, options_json: str, origin: str) -> dict:
        options = json.loads(options_json)
        rp_id = options["rp"]["id"]
        client_data = json.dumps(
            {
                "type": "webauthn.create",
                "challenge": options["challenge"],
                "origin": origin,
                "crossOrigin": False,
            }
        ).encode()
        attested = (
            bytes(16)
            + struct.pack(">H", len(self.credential_id))
            + self.credential_id
            + self._cose_key()
        )
        auth_data = (
            hashlib.sha256(rp_id.encode()).digest()
            + bytes([self._flags(FLAG_AT)])
            + struct.pack(">I", self.sign_count)
            + attested
        )
        attestation = encode_cbor({"fmt": "none", "attStmt": {}, "authData": auth_data})
        return {
            "id": b64url(self.credential_id),
            "rawId": b64url(self.credential_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64url(client_data),
                "attestationObject": b64url(attestation),
            },
        }

    def assert_(
        self,
        options_json: str,
        origin: str,
        *,
        rp_id: str | None = None,
        challenge: str | None = None,
        credential_id: bytes | None = None,
    ) -> dict:
        options = json.loads(options_json)
        self.sign_count += 1
        client_data = json.dumps(
            {
                "type": "webauthn.get",
                "challenge": challenge or options["challenge"],
                "origin": origin,
                "crossOrigin": False,
            }
        ).encode()
        auth_data = (
            hashlib.sha256((rp_id or options["rpId"]).encode()).digest()
            + bytes([self._flags()])
            + struct.pack(">I", self.sign_count)
        )
        signature = self.key.sign(
            auth_data + hashlib.sha256(client_data).digest(), ec.ECDSA(hashes.SHA256())
        )
        cid = credential_id or self.credential_id
        return {
            "id": b64url(cid),
            "rawId": b64url(cid),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64url(client_data),
                "authenticatorData": b64url(auth_data),
                "signature": b64url(signature),
                "userHandle": None,
            },
        }

"""Passkey registration and subject-bound approval (blueprint §13.1; DECISIONS.md A2).

The approval page is rendered from the server's immutable record; the challenge is bound
to that record's hash; the assertion is verified by `py_webauthn` with explicit origin,
RP ID, credential ownership, user verification and sign-count checks; and the challenge
is consumed and the approval recorded in one transaction.
"""

import hashlib
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import select, update
from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.approvals.models import Approval, ApprovalChallenge, AuthCredential, RegistrationChallenge
from app.clock import Clock
from app.controls.service import audit
from app.durable import outbox
from app.errors import ErrorCode, TrollieError

CHALLENGE_TTL = timedelta(minutes=5)


@dataclass(frozen=True)
class WebAuthnConfig:
    rp_id: str
    origin: str
    rp_name: str = "Trollie (simulated)"


class Subject(Protocol):
    """Something a customer can approve: a firm quote, or a mandate version (W3)."""

    def current_hash(
        self,
        session: Session,
        account_id: uuid.UUID,
        subject_id: uuid.UUID,
        now: datetime,
        *,
        lock: bool,
    ) -> tuple[str, datetime]:
        """Return (hash, latest valid approval time), or raise if not approvable now."""

    def on_approved(self, session: Session, subject_id: uuid.UUID, approval: Approval) -> None: ...


SUBJECTS: dict[str, Subject] = {}


def _invalid(reason: str) -> TrollieError:
    return TrollieError(ErrorCode.APPROVAL_INVALID, "approval rejected", reason=reason)


# --- Registration --------------------------------------------------------------------


def begin_registration(
    session: Session, cfg: WebAuthnConfig, *, account_id: uuid.UUID, display_name: str, clock: Clock
) -> tuple[uuid.UUID, str]:
    challenge = secrets.token_bytes(32)
    existing = session.scalars(
        select(AuthCredential.credential_id).where(
            AuthCredential.account_id == account_id, AuthCredential.revoked_at.is_(None)
        )
    ).all()
    options = generate_registration_options(
        rp_id=cfg.rp_id,
        rp_name=cfg.rp_name,
        user_name=display_name,
        user_id=account_id.bytes,
        challenge=challenge,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            # Any user-verification method (PIN or biometric) is acceptable (T22).
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=c) for c in existing],
    )
    row = RegistrationChallenge(
        account_id=account_id, challenge=challenge, expires_at=clock.now() + CHALLENGE_TTL
    )
    session.add(row)
    session.flush()
    return row.id, options_to_json(options)


def finish_registration(
    session: Session,
    cfg: WebAuthnConfig,
    *,
    account_id: uuid.UUID,
    challenge_id: uuid.UUID,
    credential: dict[str, Any] | str,
    clock: Clock,
) -> AuthCredential:
    row = session.get(RegistrationChallenge, challenge_id, with_for_update=True)
    now = clock.now()
    if row is None or row.account_id != account_id:
        raise _invalid("unknown_challenge")
    if row.consumed_at is not None:
        raise _invalid("challenge_already_used")
    if row.expires_at <= now:
        raise _invalid("challenge_expired")
    try:
        verified = verify_registration_response(
            credential=credential,
            expected_challenge=row.challenge,
            expected_rp_id=cfg.rp_id,
            expected_origin=cfg.origin,
            require_user_verification=True,
        )
    except InvalidRegistrationResponse as exc:
        raise _invalid(f"registration_failed: {exc}") from exc
    row.consumed_at = now
    cred = AuthCredential(
        account_id=account_id,
        credential_id=verified.credential_id,
        public_key=verified.credential_public_key,
        sign_count=verified.sign_count,
        user_verified_at_registration=True,
    )
    session.add(cred)
    audit(
        session,
        actor=f"account:{account_id}",
        action="credential.register",
        object_type="auth_credential",
        object_id=cred.id,
    )
    session.flush()
    return cred


# --- Approval ------------------------------------------------------------------------


def begin_approval(
    session: Session,
    cfg: WebAuthnConfig,
    *,
    account_id: uuid.UUID,
    subject_type: str,
    subject_id: uuid.UUID,
    clock: Clock,
) -> tuple[uuid.UUID, str]:
    subject = SUBJECTS[subject_type]
    now = clock.now()
    subject_hash, valid_until = subject.current_hash(
        session, account_id, subject_id, now, lock=False
    )
    creds = session.scalars(
        select(AuthCredential.credential_id).where(
            AuthCredential.account_id == account_id, AuthCredential.revoked_at.is_(None)
        )
    ).all()
    if not creds:
        raise TrollieError(ErrorCode.APPROVAL_INVALID, "no passkey registered")
    challenge = secrets.token_bytes(32)
    row = ApprovalChallenge(
        account_id=account_id,
        subject_type=subject_type,
        subject_id=subject_id,
        subject_hash=subject_hash,
        challenge=challenge,
        rp_id=cfg.rp_id,
        origin=cfg.origin,
        expires_at=min(now + CHALLENGE_TTL, valid_until),
    )
    session.add(row)
    session.flush()
    options = generate_authentication_options(
        rp_id=cfg.rp_id,
        challenge=challenge,
        allow_credentials=[PublicKeyCredentialDescriptor(id=c) for c in creds],
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    return row.id, options_to_json(options)


def _raw_id(credential: dict[str, Any] | str) -> bytes:
    data = json.loads(credential) if isinstance(credential, str) else credential
    try:
        return base64url_to_bytes(data["rawId"])
    except (KeyError, TypeError, ValueError) as exc:
        raise _invalid("malformed_credential") from exc


def verify_approval(
    session: Session,
    cfg: WebAuthnConfig,
    *,
    account_id: uuid.UUID,
    challenge_id: uuid.UUID,
    credential: dict[str, Any] | str,
    clock: Clock,
) -> Approval:
    now = clock.now()
    row = session.get(ApprovalChallenge, challenge_id, with_for_update=True, populate_existing=True)
    if row is None or row.account_id != account_id:
        raise _invalid("unknown_challenge")
    if row.consumed_at is not None:
        raise _invalid("challenge_already_used")  # T20
    if row.expires_at <= now:
        raise _invalid("challenge_expired")
    if row.origin != cfg.origin or row.rp_id != cfg.rp_id:
        raise _invalid("configuration_mismatch")

    subject = SUBJECTS[row.subject_type]
    current, _ = subject.current_hash(session, account_id, row.subject_id, now, lock=True)
    if current != row.subject_hash:
        raise TrollieError(ErrorCode.REAPPROVAL_REQUIRED, "the approved record changed")

    cred = session.scalars(
        select(AuthCredential)
        .where(AuthCredential.credential_id == _raw_id(credential))
        .with_for_update()
    ).one_or_none()
    if cred is None or cred.account_id != account_id or cred.revoked_at is not None:
        raise _invalid("credential_not_allowed")  # T21
    try:
        verified = verify_authentication_response(
            credential=credential,
            expected_challenge=row.challenge,
            expected_rp_id=cfg.rp_id,
            expected_origin=cfg.origin,
            credential_public_key=cred.public_key,
            credential_current_sign_count=cred.sign_count,
            require_user_verification=True,
        )
    except InvalidAuthenticationResponse as exc:
        raise _invalid(f"assertion_failed: {exc}") from exc

    consumed = session.execute(
        update(ApprovalChallenge)
        .where(ApprovalChallenge.id == row.id, ApprovalChallenge.consumed_at.is_(None))
        .values(consumed_at=now)
    ).rowcount
    if consumed != 1:
        raise _invalid("challenge_already_used")
    cred.sign_count = verified.new_sign_count
    data = json.loads(credential) if isinstance(credential, str) else credential
    auth_data = base64url_to_bytes(data["response"]["authenticatorData"])
    approval = Approval(
        challenge_id=row.id,
        account_id=account_id,
        subject_type=row.subject_type,
        subject_id=row.subject_id,
        subject_hash=row.subject_hash,
        credential_id=cred.id,
        user_verified=verified.user_verified,
        sign_count=verified.new_sign_count,
        authenticator_data_sha256=hashlib.sha256(auth_data).hexdigest(),
    )
    session.add(approval)
    session.flush()
    subject.on_approved(session, row.subject_id, approval)
    outbox.emit(
        session,
        aggregate_type=row.subject_type,
        aggregate_id=row.subject_id,
        aggregate_version=1,
        event_type=f"{row.subject_type}.approved",
        payload={"approval_id": str(approval.id), "subject_hash": row.subject_hash},
    )
    audit(
        session,
        actor=f"account:{account_id}",
        action=f"{row.subject_type}.approve",
        object_type=row.subject_type,
        object_id=row.subject_id,
        approval_id=str(approval.id),
    )
    return approval

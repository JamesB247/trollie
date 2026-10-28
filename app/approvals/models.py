import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, created_at, uuid_pk


class AuthCredential(Base):
    """A passkey. Approval evidence survives the credential's later revocation."""

    __tablename__ = "auth_credentials"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_accounts.id"), index=True)
    credential_id: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    public_key: Mapped[bytes] = mapped_column(LargeBinary)
    sign_count: Mapped[int] = mapped_column(default=0)
    user_verified_at_registration: Mapped[bool]
    created_at: Mapped[datetime] = created_at()
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RegistrationChallenge(Base):
    __tablename__ = "registration_challenges"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_accounts.id"))
    challenge: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()


class ApprovalChallenge(Base):
    """Single-use challenge bound to one account, one subject and its exact hash."""

    __tablename__ = "approval_challenges"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_accounts.id"), index=True)
    subject_type: Mapped[str] = mapped_column(Text)
    subject_id: Mapped[uuid.UUID]
    subject_hash: Mapped[str] = mapped_column(Text)
    challenge: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    rp_id: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()


class Approval(Base):
    """Verified consent evidence. Append-only; one per challenge."""

    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = uuid_pk()
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("approval_challenges.id"), unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_accounts.id"), index=True)
    subject_type: Mapped[str] = mapped_column(Text)
    subject_id: Mapped[uuid.UUID] = mapped_column(index=True)
    subject_hash: Mapped[str] = mapped_column(Text)
    credential_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_credentials.id"))
    user_verified: Mapped[bool]
    sign_count: Mapped[int]
    authenticator_data_sha256: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()

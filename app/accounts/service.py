import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounts.crypto import AddressCipher
from app.accounts.models import AddressVersion, CustomerAccount, LoyaltyMembership
from app.errors import ErrorCode, TrollieError


def add_address_version(
    session: Session,
    cipher: AddressCipher,
    *,
    account_id: uuid.UUID,
    label: str,
    address_text: str,
    service_zone: str,
    validated: bool = True,
) -> AddressVersion:
    """Create the next immutable version of a named address. Fictional addresses only."""
    session.get(CustomerAccount, account_id, with_for_update=True)
    current = session.scalar(
        select(func.max(AddressVersion.version)).where(
            AddressVersion.account_id == account_id, AddressVersion.label == label
        )
    )
    version_id = uuid.uuid4()
    key_id, nonce, ciphertext = cipher.encrypt(
        address_text, account_id=account_id, address_version_id=version_id
    )
    row = AddressVersion(
        id=version_id,
        account_id=account_id,
        label=label,
        version=(current or 0) + 1,
        key_id=key_id,
        nonce=nonce,
        ciphertext=ciphertext,
        service_zone=service_zone,
        validated=validated,
    )
    session.add(row)
    session.flush()
    return row


def owned_address(session: Session, account_id: uuid.UUID, version_id: uuid.UUID) -> AddressVersion:
    """Fetch an address version only if it belongs to the account (T49)."""
    row = session.get(AddressVersion, version_id)
    if row is None or row.account_id != account_id:
        raise TrollieError(ErrorCode.NOT_FOUND, "address not found")
    return row


def verified_programmes(session: Session, account_id: uuid.UUID) -> set[str]:
    return set(
        session.scalars(
            select(LoyaltyMembership.programme).where(
                LoyaltyMembership.account_id == account_id,
                LoyaltyMembership.verified_at.is_not(None),
            )
        )
    )

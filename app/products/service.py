import uuid

from sqlalchemy.orm import Session

from app.controls.service import audit
from app.errors import ErrorCode, TrollieError
from app.products.models import MatchLevel, ProductMapping


def confirm_mapping(
    session: Session, mapping_id: uuid.UUID, *, confirmed_by: str, evidence: str
) -> ProductMapping:
    """Promote a suggested mapping to USER_CONFIRMED as a new auditable revision.

    Only an explicit confirmation does this; a draft from a photo or a model never does (T03).
    """
    current = session.get(ProductMapping, mapping_id, with_for_update=True)
    if current is None or not current.active:
        raise TrollieError(ErrorCode.NOT_FOUND, "active mapping not found")
    if current.match_level != MatchLevel.SUGGESTED:
        raise TrollieError(ErrorCode.VALIDATION_FAILED, "mapping is already orderable")
    current.active = False
    session.flush()
    confirmed = ProductMapping(
        merchant_id=current.merchant_id,
        merchant_sku=current.merchant_sku,
        product_id=current.product_id,
        revision=current.revision + 1,
        match_level=MatchLevel.USER_CONFIRMED,
        evidence=evidence,
    )
    session.add(confirmed)
    audit(
        session,
        actor=confirmed_by,
        action="product_mapping.confirm",
        object_type="product_mapping",
        object_id=current.id,
        merchant_sku=current.merchant_sku,
    )
    session.flush()
    return confirmed

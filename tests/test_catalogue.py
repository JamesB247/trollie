"""Catalogue: T01 (exact verified item), T03 (unconfirmed match not orderable), scope filters,
immutability, address encryption (D-S03.5) and redaction."""

import uuid
from datetime import timedelta

import pytest
from cryptography.exceptions import InvalidTag
from sqlalchemy import select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.accounts.crypto import AddressCipher
from app.accounts.models import CustomerAccount
from app.accounts.service import add_address_version, owned_address
from app.errors import TrollieError
from app.merchants.models import Merchant, MerchantState
from app.offers.models import OfferVersion, StockConfidence
from app.offers.service import orderable_offers
from app.products.models import MatchLevel, Product, ProductMapping, gtin_is_valid
from app.products.service import confirm_mapping
from app.redaction import REDACTED, redact, redact_text
from app.seed import PRODUCTS
from tests.conftest import T0


def test_t01_exact_item_with_verified_mapping(db: Session, catalogue):
    milk = catalogue["product:milk-1l"]
    offers = orderable_offers(db, product_ids={milk}, zone="zone-a", now=T0)
    by_location = {o.location_id: o for o in offers}
    kestrel = by_location[catalogue["location:kestrel"]]
    product = db.get(Product, kestrel.product_id)
    assert (product.name, product.variant, product.pack_count, product.unit_measure) == (
        "UHT milk",
        "full cream",
        1,
        1000,
    )
    assert kestrel.merchant_id == catalogue["merchant:kestrel"]
    assert kestrel.price_minor == 1899 and kestrel.match_level == MatchLevel.GTIN_VERIFIED
    # The 6-pack and low-fat variants are distinct products, never returned for this request.
    assert all(o.product_id == milk for o in offers)


def test_seed_gtins_are_valid_and_unique(db: Session, catalogue):
    gtins = list(
        db.scalars(
            select(Product.gtin).where(
                Product.id.in_([catalogue[f"product:{p.code}"] for p in PRODUCTS])
            )
        )
    )
    assert len(gtins) == len(set(gtins)) == len(PRODUCTS)
    assert all(gtin_is_valid(g) and g.startswith("2") for g in gtins)


@pytest.mark.parametrize(
    "gtin,ok",
    [("4006381333931", True), ("4006381333932", False), ("40063813", False), ("abc", False)],
)
def test_gtin_check_digit(gtin, ok):
    assert gtin_is_valid(gtin) is ok


def test_zone_filters_unserviceable_locations(db: Session, catalogue):
    milk = catalogue["product:milk-1l"]
    zone_b = {
        o.location_id for o in orderable_offers(db, product_ids={milk}, zone="zone-b", now=T0)
    }
    assert catalogue["location:umoya"] not in zone_b  # nearby is not serviceable
    assert catalogue["location:jacaranda"] in zone_b


def _custom_product(db: Session, *, ambient=True, regulated=False) -> uuid.UUID:
    pid = uuid.uuid4()
    db.add(
        Product(
            id=pid,
            brand="Test Brand (Fictional)",
            name="Test item",
            unit_measure=1,
            unit="each",
            category="test",
            ambient=ambient,
            regulated=regulated,
        )
    )
    db.flush()
    return pid


def _offer(
    db: Session,
    catalogue,
    pid: uuid.UUID,
    *,
    level=MatchLevel.GTIN_VERIFIED,
    stock=5,
    observed=T0 - timedelta(minutes=1),
    valid=T0 + timedelta(hours=1),
    price=1000,
    merchant="kestrel",
) -> str:
    sku = f"SKU-{uuid.uuid4()}"
    db.add(
        ProductMapping(
            merchant_id=catalogue[f"merchant:{merchant}"],
            merchant_sku=sku,
            product_id=pid,
            match_level=level,
            evidence="test",
        )
    )
    db.add(
        OfferVersion(
            location_id=catalogue[f"location:{merchant}"],
            product_id=pid,
            merchant_sku=sku,
            price_minor=price,
            tax_code="standard",
            stock_quantity=stock,
            stock_confidence=StockConfidence.OBSERVED,
            observed_at=observed,
            valid_until=valid,
        )
    )
    db.flush()
    return sku


def _orderable(db: Session, pid: uuid.UUID) -> list:
    return orderable_offers(db, product_ids={pid}, zone="zone-a", now=T0)


def test_t03_suggested_match_is_not_orderable_until_user_confirms(db: Session, catalogue):
    pid = _custom_product(db)
    sku = _offer(db, catalogue, pid, level=MatchLevel.SUGGESTED)
    assert _orderable(db, pid) == []
    mapping = db.scalars(select(ProductMapping).where(ProductMapping.merchant_sku == sku)).one()
    confirmed = confirm_mapping(db, mapping.id, confirmed_by="customer:test", evidence="user tap")
    assert confirmed.revision == 2 and confirmed.match_level == MatchLevel.USER_CONFIRMED
    assert len(_orderable(db, pid)) == 1
    db.rollback()


def test_pilot_scope_excludes_regulated_and_non_ambient(db: Session, catalogue):
    for kwargs in ({"regulated": True}, {"ambient": False}):
        pid = _custom_product(db, **kwargs)
        _offer(db, catalogue, pid)
        assert _orderable(db, pid) == []
    db.rollback()


def test_zero_stock_expired_and_future_observations_excluded(db: Session, catalogue):
    for kwargs in (
        {"stock": 0},
        {"valid": T0 - timedelta(seconds=1)},
        {"observed": T0 + timedelta(minutes=1)},
    ):
        pid = _custom_product(db)
        _offer(db, catalogue, pid, **kwargs)
        assert _orderable(db, pid) == [], kwargs
    db.rollback()


def test_latest_observation_is_current(db: Session, catalogue):
    pid = _custom_product(db)
    sku = _offer(db, catalogue, pid, price=1000, observed=T0 - timedelta(minutes=10))
    db.add(
        OfferVersion(
            location_id=catalogue["location:kestrel"],
            product_id=pid,
            merchant_sku=sku,
            price_minor=1200,
            tax_code="standard",
            stock_quantity=3,
            stock_confidence="observed",
            observed_at=T0 - timedelta(minutes=2),
            valid_until=T0 + timedelta(hours=1),
        )
    )
    db.flush()
    assert [o.price_minor for o in _orderable(db, pid)] == [1200]
    db.rollback()


def test_suspended_merchant_offers_not_orderable(db: Session, catalogue):
    db.execute(
        update(Merchant)
        .where(Merchant.id == catalogue["merchant:baobab"])
        .values(state=MerchantState.SUSPENDED)
    )
    offers = orderable_offers(db, product_ids={catalogue["product:milk-1l"]}, zone="zone-a", now=T0)
    assert catalogue["location:baobab"] not in {o.location_id for o in offers}
    db.rollback()


def test_offer_versions_are_immutable(db: Session, catalogue):
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(
            text("UPDATE offer_versions SET price_minor = 1 WHERE location_id = :l"),
            {"l": catalogue["location:kestrel"]},
        )
    db.rollback()


# --- Addresses -----------------------------------------------------------------------


def _account(db: Session) -> uuid.UUID:
    acct = CustomerAccount(id=uuid.uuid4(), display_name="Test Household (Fictional)")
    db.add(acct)
    db.flush()
    return acct.id


def test_address_versions_encrypt_and_increment(db: Session):
    cipher = AddressCipher.ephemeral()
    acct = _account(db)
    v1 = add_address_version(
        db,
        cipher,
        account_id=acct,
        label="Home",
        address_text="1 Fictional Lane, Zone A",
        service_zone="zone-a",
    )
    v2 = add_address_version(
        db,
        cipher,
        account_id=acct,
        label="Home",
        address_text="2 Fictional Lane, Zone A",
        service_zone="zone-a",
    )
    assert (v1.version, v2.version) == (1, 2)
    assert b"Fictional" not in v1.ciphertext
    assert (
        cipher.decrypt(
            key_id=v1.key_id,
            nonce=v1.nonce,
            ciphertext=v1.ciphertext,
            account_id=acct,
            address_version_id=v1.id,
        )
        == "1 Fictional Lane, Zone A"
    )
    db.commit()
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(
            text("UPDATE address_versions SET service_zone = 'zone-b' WHERE id = :i"), {"i": v1.id}
        )
    db.rollback()


def test_address_ciphertext_bound_to_owner_and_version(db: Session):
    cipher = AddressCipher.ephemeral()
    acct = _account(db)
    v1 = add_address_version(
        db,
        cipher,
        account_id=acct,
        label="Home",
        address_text="1 Fictional Lane",
        service_zone="zone-a",
    )
    with pytest.raises(InvalidTag):
        cipher.decrypt(
            key_id=v1.key_id,
            nonce=v1.nonce,
            ciphertext=v1.ciphertext,
            account_id=uuid.uuid4(),
            address_version_id=v1.id,
        )
    with pytest.raises(ValueError, match="unknown address key"):
        cipher.decrypt(
            key_id="other",
            nonce=v1.nonce,
            ciphertext=v1.ciphertext,
            account_id=acct,
            address_version_id=v1.id,
        )
    db.rollback()


def test_t49_address_of_another_account_is_not_found(db: Session):
    cipher = AddressCipher.ephemeral()
    owner, other = _account(db), _account(db)
    v1 = add_address_version(
        db,
        cipher,
        account_id=owner,
        label="Home",
        address_text="1 Fictional Lane",
        service_zone="zone-a",
    )
    with pytest.raises(TrollieError):
        owned_address(db, other, v1.id)
    db.rollback()


def test_key_file_created_with_private_permissions(tmp_path):
    path = tmp_path / "address_key"
    cipher = AddressCipher.from_file(path)
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    assert AddressCipher.from_file(path).active_key_id == cipher.active_key_id


# --- Redaction -----------------------------------------------------------------------


def test_redaction_of_card_and_id_numbers():
    assert redact_text("card 4111 1111 1111 1111 ok") == f"card {REDACTED} ok"
    assert redact_text("id 8001015009087") == f"id {REDACTED}"
    assert redact_text("order total 110000 cents") == "order total 110000 cents"
    assert redact({"cvv": "123", "nested": {"pan": "x"}, "note": "fine"}) == {
        "cvv": REDACTED,
        "nested": {"pan": REDACTED},
        "note": "fine",
    }


def test_redaction_preserves_identifiers_and_hashes():
    all_digit_uuid = "12345678-1234-4123-8123-123456789012"
    digest = "ab1234567890123456cd"
    assert redact_text(f"bad:{all_digit_uuid}") == f"bad:{all_digit_uuid}"
    assert redact_text(digest) == digest
    assert redact_text(f"{all_digit_uuid} 4111111111111111") == f"{all_digit_uuid} {REDACTED}"

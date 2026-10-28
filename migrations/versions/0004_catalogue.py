"""Accounts, merchants, products, mappings, offers, promotions, delivery slots (blueprint §7.2)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

IMMUTABLE = ("offer_versions", "promotions", "address_versions")

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_customer_accounts")),
    )
    op.create_table(
        "merchants",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("legal_name", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("payout_destination_version", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_merchants")),
        sa.UniqueConstraint("code", name=op.f("uq_merchants_code")),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("gtin", sa.Text(), nullable=True),
        sa.Column("brand", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("variant", sa.Text(), nullable=False),
        sa.Column("unit_measure", sa.BigInteger(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=False),
        sa.Column("pack_count", sa.BigInteger(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("ambient", sa.Boolean(), nullable=False),
        sa.Column("regulated", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("gtin", name=op.f("uq_products_gtin")),
    )
    op.create_table(
        "address_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("key_id", sa.Text(), nullable=False),
        sa.Column("nonce", sa.LargeBinary(), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("service_zone", sa.Text(), nullable=False),
        sa.Column("validated", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["customer_accounts.id"],
            name=op.f("fk_address_versions_account_id_customer_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_address_versions")),
        sa.UniqueConstraint(
            "account_id",
            "label",
            "version",
            name=op.f("uq_address_versions_account_id_label_version"),
        ),
    )
    op.create_index(
        op.f("ix_address_versions_account_id"), "address_versions", ["account_id"], unique=False
    )
    op.create_table(
        "loyalty_memberships",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("programme", sa.Text(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["customer_accounts.id"],
            name=op.f("fk_loyalty_memberships_account_id_customer_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_loyalty_memberships")),
        sa.UniqueConstraint(
            "account_id", "programme", name=op.f("uq_loyalty_memberships_account_id_programme")
        ),
    )
    op.create_table(
        "merchant_locations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("merchant_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("service_zones", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("minimum_order_minor", sa.BigInteger(), nullable=False),
        sa.Column("pick_minutes", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"],
            ["merchants.id"],
            name=op.f("fk_merchant_locations_merchant_id_merchants"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_merchant_locations")),
        sa.UniqueConstraint("code", name=op.f("uq_merchant_locations_code")),
    )
    op.create_index(
        op.f("ix_merchant_locations_merchant_id"),
        "merchant_locations",
        ["merchant_id"],
        unique=False,
    )
    op.create_table(
        "product_mappings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("merchant_id", sa.UUID(), nullable=False),
        sa.Column("merchant_sku", sa.Text(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("match_level", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"],
            ["merchants.id"],
            name=op.f("fk_product_mappings_merchant_id_merchants"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_product_mappings_product_id_products")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_mappings")),
        sa.UniqueConstraint(
            "merchant_id",
            "merchant_sku",
            "revision",
            name=op.f("uq_product_mappings_merchant_id_merchant_sku_revision"),
        ),
    )
    op.create_index(
        "uq_product_mappings_active_sku",
        "product_mappings",
        ["merchant_id", "merchant_sku"],
        unique=True,
        postgresql_where=sa.text("active"),
    )
    op.create_table(
        "delivery_slots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("courier_code", sa.Text(), nullable=False),
        sa.Column("zone", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fee_minor", sa.BigInteger(), nullable=False),
        sa.Column("capacity", sa.BigInteger(), nullable=False),
        sa.Column("booked", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("booked <= capacity", name=op.f("ck_delivery_slots_within_capacity")),
        sa.CheckConstraint("ends_at > starts_at", name=op.f("ck_delivery_slots_window_order")),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["merchant_locations.id"],
            name=op.f("fk_delivery_slots_location_id_merchant_locations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_delivery_slots")),
    )
    op.create_index(
        op.f("ix_delivery_slots_location_id"), "delivery_slots", ["location_id"], unique=False
    )
    op.create_table(
        "merchant_capabilities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("can_reserve", sa.Boolean(), nullable=False),
        sa.Column("can_commit", sa.Boolean(), nullable=False),
        sa.Column("can_cancel", sa.Boolean(), nullable=False),
        sa.Column("can_lookup_by_reference", sa.Boolean(), nullable=False),
        sa.Column("reservation_ttl_seconds", sa.BigInteger(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["merchant_locations.id"],
            name=op.f("fk_merchant_capabilities_location_id_merchant_locations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_merchant_capabilities")),
        sa.UniqueConstraint(
            "location_id", "version", name=op.f("uq_merchant_capabilities_location_id_version")
        ),
    )
    op.create_table(
        "offer_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("merchant_sku", sa.Text(), nullable=False),
        sa.Column("price_minor", sa.BigInteger(), nullable=False),
        sa.Column("tax_code", sa.Text(), nullable=False),
        sa.Column("stock_quantity", sa.BigInteger(), nullable=True),
        sa.Column("stock_confidence", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("price_minor > 0", name=op.f("ck_offer_versions_price_positive")),
        sa.CheckConstraint(
            "stock_quantity IS NULL OR stock_quantity >= 0",
            name=op.f("ck_offer_versions_stock_nonneg"),
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["merchant_locations.id"],
            name=op.f("fk_offer_versions_location_id_merchant_locations"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_offer_versions_product_id_products")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_offer_versions")),
    )
    op.create_index(
        "ix_offer_versions_current",
        "offer_versions",
        ["location_id", "product_id", "observed_at"],
        unique=False,
    )
    op.create_table(
        "promotions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("product_ids", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.Column("min_quantity", sa.BigInteger(), nullable=False),
        sa.Column("min_spend_minor", sa.BigInteger(), nullable=False),
        sa.Column("benefit_minor", sa.BigInteger(), nullable=False),
        sa.Column("percent_bp", sa.BigInteger(), nullable=False),
        sa.Column("bundle_price_minor", sa.BigInteger(), nullable=True),
        sa.Column("price_minor", sa.BigInteger(), nullable=True),
        sa.Column("requires_loyalty_programme", sa.Text(), nullable=True),
        sa.Column("stackable", sa.Boolean(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["merchant_locations.id"],
            name=op.f("fk_promotions_location_id_merchant_locations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_promotions")),
    )

    for table in IMMUTABLE:
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION forbid_mutation()"
        )


def downgrade() -> None:
    for table in IMMUTABLE:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_immutable ON {table}")
    op.drop_table("promotions")
    op.drop_index("ix_offer_versions_current", table_name="offer_versions")
    op.drop_table("offer_versions")
    op.drop_table("merchant_capabilities")
    op.drop_index(op.f("ix_delivery_slots_location_id"), table_name="delivery_slots")
    op.drop_table("delivery_slots")
    op.drop_index(
        "uq_product_mappings_active_sku",
        table_name="product_mappings",
        postgresql_where=sa.text("active"),
    )
    op.drop_table("product_mappings")
    op.drop_index(op.f("ix_merchant_locations_merchant_id"), table_name="merchant_locations")
    op.drop_table("merchant_locations")
    op.drop_table("loyalty_memberships")
    op.drop_index(op.f("ix_address_versions_account_id"), table_name="address_versions")
    op.drop_table("address_versions")
    op.drop_table("products")
    op.drop_table("merchants")
    op.drop_table("customer_accounts")

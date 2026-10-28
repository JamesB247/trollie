"""Sessions, requested items, quotes, reservations, approvals, simulator state (blueprint §5, §13.1)

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

GUARDS = """
-- A quote's payload never changes; only its state projection and replacement link may.
CREATE FUNCTION quote_payload_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'quotes is append-only' USING ERRCODE = 'check_violation';
  END IF;
  IF (NEW.id, NEW.session_id, NEW.account_id, NEW.version, NEW.kind, NEW.strategy,
      NEW.derived_from_id, NEW.snapshot, NEW.quote_hash, NEW.total_minor,
      NEW.maximum_payable_minor, NEW.expires_at, NEW.created_at)
     IS DISTINCT FROM
     (OLD.id, OLD.session_id, OLD.account_id, OLD.version, OLD.kind, OLD.strategy,
      OLD.derived_from_id, OLD.snapshot, OLD.quote_hash, OLD.total_minor,
      OLD.maximum_payable_minor, OLD.expires_at, OLD.created_at) THEN
    RAISE EXCEPTION 'quote payload is immutable' USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER quotes_payload_immutable BEFORE UPDATE OR DELETE ON quotes
  FOR EACH ROW EXECUTE FUNCTION quote_payload_immutable();
CREATE TRIGGER quote_legs_append_only BEFORE UPDATE OR DELETE ON quote_legs
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
CREATE TRIGGER approvals_append_only BEFORE UPDATE OR DELETE ON approvals
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
"""

DROP_GUARDS = """
DROP TRIGGER IF EXISTS approvals_append_only ON approvals;
DROP TRIGGER IF EXISTS quote_legs_append_only ON quote_legs;
DROP FUNCTION IF EXISTS quote_payload_immutable CASCADE;
"""

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sim_faults",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("system", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("remaining", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sim_faults")),
    )
    op.create_table(
        "sim_merchant_orders",
        sa.Column("client_ref", sa.Text(), nullable=False),
        sa.Column("merchant_ref", sa.Text(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("reservation_ref", sa.Text(), nullable=False),
        sa.Column("lines", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("client_ref", name=op.f("pk_sim_merchant_orders")),
        sa.UniqueConstraint("merchant_ref", name=op.f("uq_sim_merchant_orders_merchant_ref")),
    )
    op.create_table(
        "sim_merchant_reservations",
        sa.Column("client_ref", sa.Text(), nullable=False),
        sa.Column("merchant_ref", sa.Text(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("lines", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("client_ref", name=op.f("pk_sim_merchant_reservations")),
        sa.UniqueConstraint("merchant_ref", name=op.f("uq_sim_merchant_reservations_merchant_ref")),
    )
    op.create_table(
        "sim_merchant_stock",
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("on_hand", sa.BigInteger(), nullable=False),
        sa.Column("held", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("location_id", "product_id", name=op.f("pk_sim_merchant_stock")),
    )
    op.create_table(
        "approval_challenges",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("subject_type", sa.Text(), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=False),
        sa.Column("subject_hash", sa.Text(), nullable=False),
        sa.Column("challenge", sa.LargeBinary(), nullable=False),
        sa.Column("rp_id", sa.Text(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["customer_accounts.id"],
            name=op.f("fk_approval_challenges_account_id_customer_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_challenges")),
        sa.UniqueConstraint("challenge", name=op.f("uq_approval_challenges_challenge")),
    )
    op.create_index(
        op.f("ix_approval_challenges_account_id"),
        "approval_challenges",
        ["account_id"],
        unique=False,
    )
    op.create_table(
        "auth_credentials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.BigInteger(), nullable=False),
        sa.Column("user_verified_at_registration", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["customer_accounts.id"],
            name=op.f("fk_auth_credentials_account_id_customer_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_credentials")),
        sa.UniqueConstraint("credential_id", name=op.f("uq_auth_credentials_credential_id")),
    )
    op.create_index(
        op.f("ix_auth_credentials_account_id"), "auth_credentials", ["account_id"], unique=False
    )
    op.create_table(
        "registration_challenges",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("challenge", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["customer_accounts.id"],
            name=op.f("fk_registration_challenges_account_id_customer_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_registration_challenges")),
        sa.UniqueConstraint("challenge", name=op.f("uq_registration_challenges_challenge")),
    )
    op.create_table(
        "approvals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("challenge_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("subject_type", sa.Text(), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=False),
        sa.Column("subject_hash", sa.Text(), nullable=False),
        sa.Column("credential_id", sa.UUID(), nullable=False),
        sa.Column("user_verified", sa.Boolean(), nullable=False),
        sa.Column("sign_count", sa.BigInteger(), nullable=False),
        sa.Column("authenticator_data_sha256", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["customer_accounts.id"],
            name=op.f("fk_approvals_account_id_customer_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["challenge_id"],
            ["approval_challenges.id"],
            name=op.f("fk_approvals_challenge_id_approval_challenges"),
        ),
        sa.ForeignKeyConstraint(
            ["credential_id"],
            ["auth_credentials.id"],
            name=op.f("fk_approvals_credential_id_auth_credentials"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approvals")),
        sa.UniqueConstraint("challenge_id", name=op.f("uq_approvals_challenge_id")),
    )
    op.create_index(op.f("ix_approvals_account_id"), "approvals", ["account_id"], unique=False)
    op.create_index(op.f("ix_approvals_subject_id"), "approvals", ["subject_id"], unique=False)
    op.create_table(
        "reservations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("merchant_id", sa.UUID(), nullable=False),
        sa.Column("client_ref", sa.Text(), nullable=False),
        sa.Column("lines", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("lines_hash", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("merchant_ref", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["merchant_locations.id"],
            name=op.f("fk_reservations_location_id_merchant_locations"),
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"], ["merchants.id"], name=op.f("fk_reservations_merchant_id_merchants")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reservations")),
        sa.UniqueConstraint("client_ref", name=op.f("uq_reservations_client_ref")),
    )
    op.create_index(
        op.f("ix_reservations_location_id"), "reservations", ["location_id"], unique=False
    )
    op.create_table(
        "shopping_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("address_version_id", sa.UUID(), nullable=False),
        sa.Column("budget_minor", sa.BigInteger(), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["customer_accounts.id"],
            name=op.f("fk_shopping_sessions_account_id_customer_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["address_version_id"],
            ["address_versions.id"],
            name=op.f("fk_shopping_sessions_address_version_id_address_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shopping_sessions")),
    )
    op.create_index(
        op.f("ix_shopping_sessions_account_id"), "shopping_sessions", ["account_id"], unique=False
    )
    op.create_table(
        "quotes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("strategy", sa.Text(), nullable=False),
        sa.Column("derived_from_id", sa.UUID(), nullable=True),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quote_hash", sa.Text(), nullable=False),
        sa.Column("total_minor", sa.BigInteger(), nullable=False),
        sa.Column("maximum_payable_minor", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("state_version", sa.BigInteger(), nullable=False),
        sa.Column("replaced_by_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["customer_accounts.id"],
            name=op.f("fk_quotes_account_id_customer_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["derived_from_id"], ["quotes.id"], name=op.f("fk_quotes_derived_from_id_quotes")
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_id"], ["quotes.id"], name=op.f("fk_quotes_replaced_by_id_quotes")
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["shopping_sessions.id"],
            name=op.f("fk_quotes_session_id_shopping_sessions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quotes")),
        sa.UniqueConstraint("quote_hash", name=op.f("uq_quotes_quote_hash")),
        sa.UniqueConstraint("session_id", "version", name=op.f("uq_quotes_session_id_version")),
    )
    op.create_index(op.f("ix_quotes_account_id"), "quotes", ["account_id"], unique=False)
    op.create_index(op.f("ix_quotes_session_id"), "quotes", ["session_id"], unique=False)
    op.create_table(
        "requested_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("line_id", sa.Text(), nullable=False),
        sa.Column("rule", sa.Text(), nullable=False),
        sa.Column("candidates", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quantity_packs", sa.BigInteger(), nullable=True),
        sa.Column("quantity_measure", sa.BigInteger(), nullable=True),
        sa.Column("quantity_unit", sa.Text(), nullable=True),
        sa.Column("must_have", sa.Boolean(), nullable=False),
        sa.Column("needs_clarification", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(quantity_packs IS NOT NULL) <> (quantity_measure IS NOT NULL)",
            name=op.f("ck_requested_items_one_quantity"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["shopping_sessions.id"],
            name=op.f("fk_requested_items_session_id_shopping_sessions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_requested_items")),
        sa.UniqueConstraint(
            "session_id", "line_id", name=op.f("uq_requested_items_session_id_line_id")
        ),
    )
    op.create_index(
        op.f("ix_requested_items_session_id"), "requested_items", ["session_id"], unique=False
    )
    op.create_table(
        "quote_legs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("quote_id", sa.UUID(), nullable=False),
        sa.Column("leg_id", sa.Text(), nullable=False),
        sa.Column("merchant_id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("reservation_id", sa.UUID(), nullable=True),
        sa.Column("slot_id", sa.UUID(), nullable=False),
        sa.Column("goods_minor", sa.BigInteger(), nullable=False),
        sa.Column("delivery_minor", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["merchant_locations.id"],
            name=op.f("fk_quote_legs_location_id_merchant_locations"),
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"], ["merchants.id"], name=op.f("fk_quote_legs_merchant_id_merchants")
        ),
        sa.ForeignKeyConstraint(
            ["quote_id"], ["quotes.id"], name=op.f("fk_quote_legs_quote_id_quotes")
        ),
        sa.ForeignKeyConstraint(
            ["reservation_id"],
            ["reservations.id"],
            name=op.f("fk_quote_legs_reservation_id_reservations"),
        ),
        sa.ForeignKeyConstraint(
            ["slot_id"], ["delivery_slots.id"], name=op.f("fk_quote_legs_slot_id_delivery_slots")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quote_legs")),
        sa.UniqueConstraint("quote_id", "leg_id", name=op.f("uq_quote_legs_quote_id_leg_id")),
    )
    op.create_index(op.f("ix_quote_legs_quote_id"), "quote_legs", ["quote_id"], unique=False)

    op.execute(GUARDS)


def downgrade() -> None:
    op.execute(DROP_GUARDS)
    op.drop_index(op.f("ix_quote_legs_quote_id"), table_name="quote_legs")
    op.drop_table("quote_legs")
    op.drop_index(op.f("ix_requested_items_session_id"), table_name="requested_items")
    op.drop_table("requested_items")
    op.drop_index(op.f("ix_quotes_session_id"), table_name="quotes")
    op.drop_index(op.f("ix_quotes_account_id"), table_name="quotes")
    op.drop_table("quotes")
    op.drop_index(op.f("ix_shopping_sessions_account_id"), table_name="shopping_sessions")
    op.drop_table("shopping_sessions")
    op.drop_index(op.f("ix_reservations_location_id"), table_name="reservations")
    op.drop_table("reservations")
    op.drop_index(op.f("ix_approvals_subject_id"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_account_id"), table_name="approvals")
    op.drop_table("approvals")
    op.drop_table("registration_challenges")
    op.drop_index(op.f("ix_auth_credentials_account_id"), table_name="auth_credentials")
    op.drop_table("auth_credentials")
    op.drop_index(op.f("ix_approval_challenges_account_id"), table_name="approval_challenges")
    op.drop_table("approval_challenges")
    op.drop_table("sim_merchant_stock")
    op.drop_table("sim_merchant_reservations")
    op.drop_table("sim_merchant_orders")
    op.drop_table("sim_faults")

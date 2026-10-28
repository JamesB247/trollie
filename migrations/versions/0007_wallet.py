"""Synthetic wallet tables (D-W01-D-W03): wallets, agents, envelopes, grants, funding.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wallet_refunds",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("business_key", sa.Text(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("destination", sa.Text(), nullable=False),
        sa.Column("economic_allocation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount_minor > 0", name=op.f("ck_wallet_refunds_amount_positive")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wallet_refunds")),
        sa.UniqueConstraint("business_key", name=op.f("uq_wallet_refunds_business_key")),
    )
    op.create_index(
        op.f("ix_wallet_refunds_order_id"), "wallet_refunds", ["order_id"], unique=False
    )
    op.create_table(
        "agents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["customer_accounts.id"],
            name=op.f("fk_agents_account_id_customer_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agents")),
    )
    op.create_index(op.f("ix_agents_account_id"), "agents", ["account_id"], unique=False)
    op.create_table(
        "wallets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("funding_reference", sa.Text(), nullable=False),
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
            name=op.f("fk_wallets_account_id_customer_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wallets")),
        sa.UniqueConstraint("account_id", name=op.f("uq_wallets_account_id")),
        sa.UniqueConstraint("funding_reference", name=op.f("uq_wallets_funding_reference")),
    )
    op.create_table(
        "funding_intents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("wallet_id", sa.UUID(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("transfer_ref", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount_minor > 0", name=op.f("ck_funding_intents_amount_positive")),
        sa.ForeignKeyConstraint(
            ["wallet_id"], ["wallets.id"], name=op.f("fk_funding_intents_wallet_id_wallets")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_funding_intents")),
        sa.UniqueConstraint("transfer_ref", name=op.f("uq_funding_intents_transfer_ref")),
    )
    op.create_index(
        op.f("ix_funding_intents_wallet_id"), "funding_intents", ["wallet_id"], unique=False
    )
    op.create_table(
        "wallet_envelopes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("wallet_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"], ["agents.id"], name=op.f("fk_wallet_envelopes_agent_id_agents")
        ),
        sa.ForeignKeyConstraint(
            ["wallet_id"], ["wallets.id"], name=op.f("fk_wallet_envelopes_wallet_id_wallets")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wallet_envelopes")),
        sa.UniqueConstraint("agent_id", name=op.f("uq_wallet_envelopes_agent_id")),
    )
    op.create_index(
        op.f("ix_wallet_envelopes_wallet_id"), "wallet_envelopes", ["wallet_id"], unique=False
    )
    op.create_table(
        "wallet_redemptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("wallet_id", sa.UUID(), nullable=False),
        sa.Column("business_key", sa.Text(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("destination", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount_minor > 0", name=op.f("ck_wallet_redemptions_amount_positive")),
        sa.ForeignKeyConstraint(
            ["wallet_id"], ["wallets.id"], name=op.f("fk_wallet_redemptions_wallet_id_wallets")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wallet_redemptions")),
        sa.UniqueConstraint("business_key", name=op.f("uq_wallet_redemptions_business_key")),
    )
    op.create_index(
        op.f("ix_wallet_redemptions_wallet_id"), "wallet_redemptions", ["wallet_id"], unique=False
    )
    op.create_table(
        "agent_grants",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("envelope_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("approval_mode", sa.Text(), nullable=False),
        sa.Column("merchant_ids", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.Column("product_ids", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.Column("categories", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("address_version_id", sa.UUID(), nullable=False),
        sa.Column("per_order_cap_minor", sa.BigInteger(), nullable=False),
        sa.Column("period_cap_minor", sa.BigInteger(), nullable=False),
        sa.Column("period_days", sa.BigInteger(), nullable=False),
        sa.Column("max_orders_per_day", sa.BigInteger(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("grant_hash", sa.Text(), nullable=False),
        sa.Column("approval_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "per_order_cap_minor > 0 AND period_cap_minor > 0",
            name=op.f("ck_agent_grants_caps_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["address_version_id"],
            ["address_versions.id"],
            name=op.f("fk_agent_grants_address_version_id_address_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"], ["agents.id"], name=op.f("fk_agent_grants_agent_id_agents")
        ),
        sa.ForeignKeyConstraint(
            ["approval_id"], ["approvals.id"], name=op.f("fk_agent_grants_approval_id_approvals")
        ),
        sa.ForeignKeyConstraint(
            ["envelope_id"],
            ["wallet_envelopes.id"],
            name=op.f("fk_agent_grants_envelope_id_wallet_envelopes"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_grants")),
        sa.UniqueConstraint("agent_id", "version", name=op.f("uq_agent_grants_agent_id_version")),
    )
    op.create_index(op.f("ix_agent_grants_agent_id"), "agent_grants", ["agent_id"], unique=False)
    op.create_table(
        "wallet_reservations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("wallet_id", sa.UUID(), nullable=False),
        sa.Column("envelope_id", sa.UUID(), nullable=True),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount_minor > 0", name=op.f("ck_wallet_reservations_amount_positive")),
        sa.ForeignKeyConstraint(
            ["envelope_id"],
            ["wallet_envelopes.id"],
            name=op.f("fk_wallet_reservations_envelope_id_wallet_envelopes"),
        ),
        sa.ForeignKeyConstraint(
            ["wallet_id"], ["wallets.id"], name=op.f("fk_wallet_reservations_wallet_id_wallets")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wallet_reservations")),
        sa.UniqueConstraint("order_id", name=op.f("uq_wallet_reservations_order_id")),
    )
    op.create_index(
        op.f("ix_wallet_reservations_wallet_id"), "wallet_reservations", ["wallet_id"], unique=False
    )
    op.create_table(
        "grant_usage",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("grant_id", sa.UUID(), nullable=False),
        sa.Column("quote_id", sa.UUID(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["grant_id"], ["agent_grants.id"], name=op.f("fk_grant_usage_grant_id_agent_grants")
        ),
        sa.ForeignKeyConstraint(
            ["quote_id"], ["quotes.id"], name=op.f("fk_grant_usage_quote_id_quotes")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grant_usage")),
        sa.UniqueConstraint("quote_id", name=op.f("uq_grant_usage_quote_id")),
    )
    op.create_index(op.f("ix_grant_usage_grant_id"), "grant_usage", ["grant_id"], unique=False)
    op.create_table(
        "mandate_executions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("grant_id", sa.UUID(), nullable=False),
        sa.Column("quote_id", sa.UUID(), nullable=False),
        sa.Column("quote_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["grant_id"],
            ["agent_grants.id"],
            name=op.f("fk_mandate_executions_grant_id_agent_grants"),
        ),
        sa.ForeignKeyConstraint(
            ["quote_id"], ["quotes.id"], name=op.f("fk_mandate_executions_quote_id_quotes")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mandate_executions")),
        sa.UniqueConstraint("quote_id", name=op.f("uq_mandate_executions_quote_id")),
    )
    op.create_index(
        op.f("ix_mandate_executions_grant_id"), "mandate_executions", ["grant_id"], unique=False
    )
    op.add_column("orders", sa.Column("mandate_execution_id", sa.UUID(), nullable=True))
    op.alter_column("orders", "approval_id", existing_type=sa.UUID(), nullable=True)
    op.create_unique_constraint(
        op.f("uq_orders_mandate_execution_id"), "orders", ["mandate_execution_id"]
    )
    op.create_foreign_key(
        op.f("fk_orders_mandate_execution_id_mandate_executions"),
        "orders",
        "mandate_executions",
        ["mandate_execution_id"],
        ["id"],
    )

    op.create_check_constraint(
        "ck_orders_one_authority", "orders", "num_nonnulls(approval_id, mandate_execution_id) = 1"
    )


def downgrade() -> None:
    op.drop_constraint("ck_orders_one_authority", "orders", type_="check")
    op.drop_constraint(
        op.f("fk_orders_mandate_execution_id_mandate_executions"), "orders", type_="foreignkey"
    )
    op.drop_constraint(op.f("uq_orders_mandate_execution_id"), "orders", type_="unique")
    op.alter_column("orders", "approval_id", existing_type=sa.UUID(), nullable=False)
    op.drop_column("orders", "mandate_execution_id")
    op.drop_index(op.f("ix_mandate_executions_grant_id"), table_name="mandate_executions")
    op.drop_table("mandate_executions")
    op.drop_index(op.f("ix_grant_usage_grant_id"), table_name="grant_usage")
    op.drop_table("grant_usage")
    op.drop_index(op.f("ix_wallet_reservations_wallet_id"), table_name="wallet_reservations")
    op.drop_table("wallet_reservations")
    op.drop_index(op.f("ix_agent_grants_agent_id"), table_name="agent_grants")
    op.drop_table("agent_grants")
    op.drop_index(op.f("ix_wallet_redemptions_wallet_id"), table_name="wallet_redemptions")
    op.drop_table("wallet_redemptions")
    op.drop_index(op.f("ix_wallet_envelopes_wallet_id"), table_name="wallet_envelopes")
    op.drop_table("wallet_envelopes")
    op.drop_index(op.f("ix_funding_intents_wallet_id"), table_name="funding_intents")
    op.drop_table("funding_intents")
    op.drop_table("wallets")
    op.drop_index(op.f("ix_agents_account_id"), table_name="agents")
    op.drop_table("agents")
    op.drop_index(op.f("ix_wallet_refunds_order_id"), table_name="wallet_refunds")
    op.drop_table("wallet_refunds")

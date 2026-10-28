"""Orders, legs, deliveries, financial operations, refunds, settlement, reconciliation.

Blueprint §8, §9, §14.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "financial_operations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=True),
        sa.Column("subject_type", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("profile_key", sa.Text(), nullable=False),
        sa.Column("profile_version", sa.BigInteger(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("request_hash", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("external_ref", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_args", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("last_observation", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount_minor > 0", name=op.f("ck_financial_operations_amount_positive")
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["financial_operations.id"],
            name=op.f("fk_financial_operations_parent_id_financial_operations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_financial_operations")),
        sa.UniqueConstraint(
            "idempotency_key", name=op.f("uq_financial_operations_idempotency_key")
        ),
    )
    op.create_index(
        op.f("ix_financial_operations_external_ref"),
        "financial_operations",
        ["external_ref"],
        unique=False,
    )
    op.create_index(
        op.f("ix_financial_operations_order_id"), "financial_operations", ["order_id"], unique=False
    )
    op.create_table(
        "reconciliation_cases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("dedupe_key", sa.Text(), nullable=False),
        sa.Column("case_type", sa.Text(), nullable=False),
        sa.Column("refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("difference_minor", sa.BigInteger(), nullable=True),
        sa.Column("owner", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("resolution_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reconciliation_cases")),
        sa.UniqueConstraint("dedupe_key", name=op.f("uq_reconciliation_cases_dedupe_key")),
    )
    op.create_table(
        "settlement_reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("report_ref", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_settlement_reports")),
        sa.UniqueConstraint("report_ref", name=op.f("uq_settlement_reports_report_ref")),
    )
    op.create_table(
        "sim_courier_bookings",
        sa.Column("booking_ref", sa.Text(), nullable=False),
        sa.Column("courier_ref", sa.Text(), nullable=False),
        sa.Column("slot_id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("address_version_id", sa.UUID(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("booking_ref", name=op.f("pk_sim_courier_bookings")),
        sa.UniqueConstraint("courier_ref", name=op.f("uq_sim_courier_bookings_courier_ref")),
    )
    op.create_table(
        "sim_payment_idempotency",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("request_hash", sa.Text(), nullable=False),
        sa.Column("provider_ref", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_sim_payment_idempotency")),
    )
    op.create_table(
        "sim_payments",
        sa.Column("provider_ref", sa.Text(), nullable=False),
        sa.Column("client_key", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("collection", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("parent_ref", sa.Text(), nullable=True),
        sa.Column("beneficiaries", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("captured_minor", sa.BigInteger(), nullable=False),
        sa.Column("refunded_minor", sa.BigInteger(), nullable=False),
        sa.Column("settled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("provider_ref", name=op.f("pk_sim_payments")),
    )
    op.create_table(
        "sim_webhooks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("deliver_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deliveries_remaining", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sim_webhooks")),
    )
    op.create_table(
        "payment_allocations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("operation_id", sa.UUID(), nullable=False),
        sa.Column("party_type", sa.Text(), nullable=False),
        sa.Column("party_id", sa.UUID(), nullable=True),
        sa.Column("provider_beneficiary", sa.Text(), nullable=False),
        sa.Column("gross_minor", sa.BigInteger(), nullable=False),
        sa.Column("fee_minor", sa.BigInteger(), nullable=True),
        sa.Column("net_minor", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["financial_operations.id"],
            name=op.f("fk_payment_allocations_operation_id_financial_operations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_allocations")),
    )
    op.create_index(
        op.f("ix_payment_allocations_operation_id"),
        "payment_allocations",
        ["operation_id"],
        unique=False,
    )
    op.create_table(
        "refunds",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("business_key", sa.Text(), nullable=False),
        sa.Column("original_operation_id", sa.UUID(), nullable=False),
        sa.Column("operation_id", sa.UUID(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("economic_allocation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provider_allocation", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("destination", sa.Text(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount_minor > 0", name=op.f("ck_refunds_amount_positive")),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["financial_operations.id"],
            name=op.f("fk_refunds_operation_id_financial_operations"),
        ),
        sa.ForeignKeyConstraint(
            ["original_operation_id"],
            ["financial_operations.id"],
            name=op.f("fk_refunds_original_operation_id_financial_operations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refunds")),
        sa.UniqueConstraint("business_key", name=op.f("uq_refunds_business_key")),
    )
    op.create_index(op.f("ix_refunds_order_id"), "refunds", ["order_id"], unique=False)
    op.create_table(
        "settlement_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("report_id", sa.UUID(), nullable=False),
        sa.Column("line_no", sa.BigInteger(), nullable=False),
        sa.Column("provider_line_ref", sa.Text(), nullable=False),
        sa.Column("operation_ref", sa.Text(), nullable=False),
        sa.Column("beneficiary", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("gross_minor", sa.BigInteger(), nullable=False),
        sa.Column("fee_minor", sa.BigInteger(), nullable=False),
        sa.Column("net_minor", sa.BigInteger(), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["settlement_reports.id"],
            name=op.f("fk_settlement_items_report_id_settlement_reports"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_settlement_items")),
        sa.UniqueConstraint(
            "provider_line_ref", name=op.f("uq_settlement_items_provider_line_ref")
        ),
        sa.UniqueConstraint(
            "report_id", "line_no", name=op.f("uq_settlement_items_report_id_line_no")
        ),
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("quote_id", sa.UUID(), nullable=False),
        sa.Column("approval_id", sa.UUID(), nullable=False),
        sa.Column("approved_hash", sa.Text(), nullable=False),
        sa.Column("execution_snapshot_hash", sa.Text(), nullable=False),
        sa.Column("funding_source", sa.Text(), nullable=False),
        sa.Column("profile_key", sa.Text(), nullable=False),
        sa.Column("address_version_id", sa.UUID(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("attention_reason", sa.Text(), nullable=True),
        sa.Column("plan", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("customer_cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["customer_accounts.id"],
            name=op.f("fk_orders_account_id_customer_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["address_version_id"],
            ["address_versions.id"],
            name=op.f("fk_orders_address_version_id_address_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["approval_id"], ["approvals.id"], name=op.f("fk_orders_approval_id_approvals")
        ),
        sa.ForeignKeyConstraint(
            ["quote_id"], ["quotes.id"], name=op.f("fk_orders_quote_id_quotes")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
        sa.UniqueConstraint("approval_id", name=op.f("uq_orders_approval_id")),
        sa.UniqueConstraint("quote_id", name=op.f("uq_orders_quote_id")),
    )
    op.create_index(op.f("ix_orders_account_id"), "orders", ["account_id"], unique=False)
    op.create_table(
        "order_legs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("leg_id", sa.Text(), nullable=False),
        sa.Column("merchant_id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("reservation_id", sa.UUID(), nullable=True),
        sa.Column("commit_ref", sa.Text(), nullable=False),
        sa.Column("merchant_ref", sa.Text(), nullable=True),
        sa.Column("goods_minor", sa.BigInteger(), nullable=False),
        sa.Column("delivery_minor", sa.BigInteger(), nullable=False),
        sa.Column("line_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
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
            name=op.f("fk_order_legs_location_id_merchant_locations"),
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"], ["merchants.id"], name=op.f("fk_order_legs_merchant_id_merchants")
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], name=op.f("fk_order_legs_order_id_orders")
        ),
        sa.ForeignKeyConstraint(
            ["reservation_id"],
            ["reservations.id"],
            name=op.f("fk_order_legs_reservation_id_reservations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_legs")),
        sa.UniqueConstraint("commit_ref", name=op.f("uq_order_legs_commit_ref")),
        sa.UniqueConstraint("order_id", "leg_id", name=op.f("uq_order_legs_order_id_leg_id")),
    )
    op.create_index(op.f("ix_order_legs_order_id"), "order_legs", ["order_id"], unique=False)
    op.create_table(
        "delivery_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_leg_id", sa.UUID(), nullable=False),
        sa.Column("slot_id", sa.UUID(), nullable=False),
        sa.Column("courier_code", sa.Text(), nullable=False),
        sa.Column("booking_ref", sa.Text(), nullable=False),
        sa.Column("courier_ref", sa.Text(), nullable=True),
        sa.Column("address_version_id", sa.UUID(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["address_version_id"],
            ["address_versions.id"],
            name=op.f("fk_delivery_jobs_address_version_id_address_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["order_leg_id"],
            ["order_legs.id"],
            name=op.f("fk_delivery_jobs_order_leg_id_order_legs"),
        ),
        sa.ForeignKeyConstraint(
            ["slot_id"], ["delivery_slots.id"], name=op.f("fk_delivery_jobs_slot_id_delivery_slots")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_delivery_jobs")),
        sa.UniqueConstraint("booking_ref", name=op.f("uq_delivery_jobs_booking_ref")),
        sa.UniqueConstraint("order_leg_id", name=op.f("uq_delivery_jobs_order_leg_id")),
    )


def downgrade() -> None:
    op.drop_table("delivery_jobs")
    op.drop_index(op.f("ix_order_legs_order_id"), table_name="order_legs")
    op.drop_table("order_legs")
    op.drop_index(op.f("ix_orders_account_id"), table_name="orders")
    op.drop_table("orders")
    op.drop_table("settlement_items")
    op.drop_index(op.f("ix_refunds_order_id"), table_name="refunds")
    op.drop_table("refunds")
    op.drop_index(op.f("ix_payment_allocations_operation_id"), table_name="payment_allocations")
    op.drop_table("payment_allocations")
    op.drop_table("sim_webhooks")
    op.drop_table("sim_payments")
    op.drop_table("sim_payment_idempotency")
    op.drop_table("sim_courier_bookings")
    op.drop_table("settlement_reports")
    op.drop_table("reconciliation_cases")
    op.drop_index(op.f("ix_financial_operations_order_id"), table_name="financial_operations")
    op.drop_index(op.f("ix_financial_operations_external_ref"), table_name="financial_operations")
    op.drop_table("financial_operations")

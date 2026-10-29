"""Merchant risk tier and onboarding date; simulated integration latency; offer lookup by
product (crowd simulation at catalogue scale).

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-29
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "merchants",
        sa.Column("risk_tier", sa.Text(), server_default="standard", nullable=False),
    )
    op.add_column("merchants", sa.Column("onboarded_at", sa.DateTime(timezone=True)))
    op.create_table(
        "sim_merchant_latency",
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("mean_ms", sa.Integer(), nullable=False),
        sa.Column("jitter_ms", sa.Integer(), nullable=False),
        sa.Column("slow_permille", sa.Integer(), nullable=False),
        sa.Column("slow_ms", sa.Integer(), nullable=False),
        sa.Column("timeout_ms", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("location_id", name=op.f("pk_sim_merchant_latency")),
    )
    op.create_index(
        "ix_offer_versions_by_product",
        "offer_versions",
        ["product_id", "location_id", "observed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_offer_versions_by_product", table_name="offer_versions")
    op.drop_table("sim_merchant_latency")
    op.drop_column("merchants", "onboarded_at")
    op.drop_column("merchants", "risk_tier")

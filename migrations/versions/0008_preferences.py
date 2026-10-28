"""User-confirmed preferences with provenance (PRD product preferences; T48)

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "preferences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("rule", sa.Text(), nullable=False),
        sa.Column("provenance", sa.Text(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["customer_accounts.id"],
            name=op.f("fk_preferences_account_id_customer_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_preferences_product_id_products")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_preferences")),
    )
    op.create_index(op.f("ix_preferences_account_id"), "preferences", ["account_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_preferences_account_id"), table_name="preferences")
    op.drop_table("preferences")

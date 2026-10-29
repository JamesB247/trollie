"""Trust controls found necessary by the crowd simulation: agent suspension and per-leg
delivery deadlines (I-043..I-047).

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-29
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("suspended_at", sa.DateTime(timezone=True)))
    op.add_column("agents", sa.Column("suspended_reason", sa.Text()))
    op.add_column("order_legs", sa.Column("window_end", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("order_legs", "window_end")
    op.drop_column("agents", "suspended_reason")
    op.drop_column("agents", "suspended_at")

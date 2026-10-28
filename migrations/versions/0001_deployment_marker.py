"""Deployment marker: records the environment a database belongs to (W20).

Revision ID: 0001
Revises:
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import context, op

from app.config import Environment, get_settings

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    env = context.config.attributes.get("environment") or get_settings().env.value
    if env == Environment.LIVE.value:
        raise RuntimeError("refusing to create a synthetic database for a live environment")
    op.create_table(
        "deployment_marker",
        sa.Column("singleton", sa.Boolean, primary_key=True, server_default=sa.true()),
        sa.Column("environment", sa.Text, nullable=False),
        sa.Column("synthetic", sa.Boolean, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("singleton", name="deployment_marker_single_row"),
        sa.CheckConstraint("environment IN ('dev', 'test', 'live')", name="deployment_marker_env"),
    )
    op.execute(
        sa.text(
            "INSERT INTO deployment_marker (environment, synthetic) VALUES (:env, true)"
        ).bindparams(env=env)
    )


def downgrade() -> None:
    op.drop_table("deployment_marker")

"""Ledger and controls, with database-level ledger invariants (blueprint §7.3; T52)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

GUARDS = """
CREATE FUNCTION forbid_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION '% is append-only', TG_TABLE_NAME USING ERRCODE = 'check_violation';
END $$;

CREATE TRIGGER ledger_transactions_append_only BEFORE UPDATE OR DELETE ON ledger_transactions
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
CREATE TRIGGER ledger_transactions_no_truncate BEFORE TRUNCATE ON ledger_transactions
  FOR EACH STATEMENT EXECUTE FUNCTION forbid_mutation();
CREATE TRIGGER ledger_entries_append_only BEFORE UPDATE OR DELETE ON ledger_entries
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
CREATE TRIGGER ledger_entries_no_truncate BEFORE TRUNCATE ON ledger_entries
  FOR EACH STATEMENT EXECUTE FUNCTION forbid_mutation();
CREATE TRIGGER audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
CREATE TRIGGER audit_events_no_truncate BEFORE TRUNCATE ON audit_events
  FOR EACH STATEMENT EXECUTE FUNCTION forbid_mutation();

-- Entries may only be added inside the database transaction that created their parent.
CREATE FUNCTION ledger_entry_same_txn() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (SELECT posted_txid FROM ledger_transactions WHERE id = NEW.transaction_id)
     IS DISTINCT FROM txid_current() THEN
    RAISE EXCEPTION 'entries cannot be added to an already posted ledger transaction'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER ledger_entries_same_txn BEFORE INSERT ON ledger_entries
  FOR EACH ROW EXECUTE FUNCTION ledger_entry_same_txn();

-- Checked at commit: at least two entries and debits = credits per currency.
CREATE FUNCTION ledger_check_balanced() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE tid uuid;
BEGIN
  IF TG_TABLE_NAME = 'ledger_entries' THEN
    tid := NEW.transaction_id;
  ELSE
    tid := NEW.id;
  END IF;
  IF (SELECT count(*) FROM ledger_entries WHERE transaction_id = tid) < 2 THEN
    RAISE EXCEPTION 'ledger transaction % has fewer than two entries', tid
      USING ERRCODE = 'check_violation';
  END IF;
  IF EXISTS (
    SELECT 1 FROM ledger_entries WHERE transaction_id = tid
    GROUP BY currency HAVING sum(debit_minor) <> sum(credit_minor)
  ) THEN
    RAISE EXCEPTION 'ledger transaction % is unbalanced', tid USING ERRCODE = 'check_violation';
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER ledger_entries_balanced AFTER INSERT ON ledger_entries
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ledger_check_balanced();
CREATE CONSTRAINT TRIGGER ledger_transactions_balanced AFTER INSERT ON ledger_transactions
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ledger_check_balanced();
"""

DROP_GUARDS = """
DROP FUNCTION IF EXISTS forbid_mutation, ledger_entry_same_txn, ledger_check_balanced CASCADE;
"""

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("object_type", sa.Text(), nullable=False),
        sa.Column("object_id", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_table(
        "incidents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incidents")),
    )
    op.create_table(
        "kill_switches",
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("engaged", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_by", sa.Text(), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("scope", name=op.f("pk_kill_switches")),
    )
    op.create_table(
        "ledger_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("owner_type", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "account_class",
            sa.Enum("asset", "liability", "revenue", "expense", "equity", name="account_class"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ledger_accounts")),
        sa.UniqueConstraint(
            "code",
            "owner_type",
            "owner_id",
            "currency",
            name="uq_ledger_accounts_natural_key",
            postgresql_nulls_not_distinct=True,
        ),
        sa.UniqueConstraint("id", "currency", name="uq_ledger_accounts_id_currency"),
    )
    op.create_table(
        "ledger_transactions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("posting_key", sa.Text(), nullable=False),
        sa.Column("entries_digest", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("business_operation_id", sa.UUID(), nullable=True),
        sa.Column("reverses_id", sa.UUID(), nullable=True),
        sa.Column(
            "posted_txid", sa.BigInteger(), server_default=sa.text("txid_current()"), nullable=False
        ),
        sa.Column(
            "posted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["reverses_id"],
            ["ledger_transactions.id"],
            name=op.f("fk_ledger_transactions_reverses_id_ledger_transactions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ledger_transactions")),
        sa.UniqueConstraint("posting_key", name=op.f("uq_ledger_transactions_posting_key")),
        sa.UniqueConstraint("reverses_id", name=op.f("uq_ledger_transactions_reverses_id")),
    )
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("transaction_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("debit_minor", sa.BigInteger(), nullable=False),
        sa.Column("credit_minor", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "(debit_minor > 0 AND credit_minor = 0) OR (credit_minor > 0 AND debit_minor = 0)",
            name=op.f("ck_ledger_entries_one_side_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "currency"],
            ["ledger_accounts.id", "ledger_accounts.currency"],
            name="fk_ledger_entries_account_currency",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["ledger_transactions.id"],
            name=op.f("fk_ledger_entries_transaction_id_ledger_transactions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ledger_entries")),
    )
    op.create_index(
        op.f("ix_ledger_entries_account_id"), "ledger_entries", ["account_id"], unique=False
    )
    op.create_index(
        op.f("ix_ledger_entries_transaction_id"), "ledger_entries", ["transaction_id"], unique=False
    )
    op.execute(GUARDS)


def downgrade() -> None:
    op.execute(DROP_GUARDS)
    op.drop_index(op.f("ix_ledger_entries_transaction_id"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_account_id"), table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_table("ledger_transactions")
    op.drop_table("ledger_accounts")
    op.drop_table("kill_switches")
    op.drop_table("incidents")
    op.drop_table("audit_events")
    sa.Enum(name="account_class").drop(op.get_bind(), checkfirst=True)

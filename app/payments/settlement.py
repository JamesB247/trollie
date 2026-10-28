"""Settlement report import and four-way reconciliation (blueprint §14.4; T36, T53, T54).

A report is imported once (by reference and content hash); each provider line is posted
once (unique line reference). Failed payouts keep the payable open. Any difference between
the report and Trollie's operations opens an owned case; nothing posts a balancing entry.
"""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.durable.hashing import canonical_hash
from app.ledger.postings import post_settlement_line
from app.orders.runtime import Runtime
from app.payments.models import (
    Action,
    FinancialOperation,
    OpState,
    SettlementItem,
    SettlementReport,
)
from app.reconciliation.service import open_case


def import_settlement(rt: Runtime, report: dict) -> str:
    content_hash = canonical_hash(report)
    with rt.sessions() as s, s.begin():
        existing = s.scalars(
            select(SettlementReport).where(SettlementReport.report_ref == report["report_ref"])
        ).first()
        if existing is not None:
            if existing.content_hash != content_hash:
                open_case(
                    s,
                    dedupe_key=f"report-changed:{report['report_ref']}:{content_hash}",
                    case_type="settlement_report_changed",
                    refs={"report_ref": report["report_ref"]},
                )
                return "conflict"
            return "duplicate"  # T53
        row = SettlementReport(
            provider=report["provider"], report_ref=report["report_ref"], content_hash=content_hash
        )
        s.add(row)
        s.flush()
        gross_by_op: dict[str, int] = {}
        for n, line in enumerate(report["lines"], start=1):
            inserted = s.execute(
                insert(SettlementItem)
                .values(
                    id=uuid.uuid4(),
                    report_id=row.id,
                    line_no=n,
                    provider_line_ref=line["line_ref"],
                    operation_ref=line["operation_ref"],
                    beneficiary=line["beneficiary"],
                    kind=line["kind"],
                    gross_minor=line["gross_minor"],
                    fee_minor=line["fee_minor"],
                    net_minor=line["net_minor"],
                    settled_at=datetime.fromisoformat(line["settled_at"]),
                )
                .on_conflict_do_nothing(index_elements=["provider_line_ref"])
                .returning(SettlementItem.id)
            ).scalar_one_or_none()
            if inserted is None:
                continue  # the same provider line in another report: never posted twice
            if line["kind"] != "fee":
                gross_by_op[line["operation_ref"]] = (
                    gross_by_op.get(line["operation_ref"], 0) + line["gross_minor"]
                )
            if line["kind"] == "payout_failed":
                # T36: the payable stays open until the payout is established.
                open_case(
                    s,
                    dedupe_key=f"payout-failed:{line['line_ref']}",
                    case_type="payout_failed",
                    refs={"line_ref": line["line_ref"], "beneficiary": line["beneficiary"]},
                    difference_minor=line["gross_minor"],
                )
                continue
            post_settlement_line(
                s,
                line_ref=line["line_ref"],
                beneficiary=line["beneficiary"],
                net_minor=line["net_minor"],
                fee_minor=line["fee_minor"],
            )
        _compare(s, gross_by_op, report["report_ref"])
    return "imported"


def _compare(s, gross_by_op: dict[str, int], report_ref: str) -> None:
    """Report gross per payment must equal what Trollie collected minus confirmed refunds."""
    for provider_ref, gross in gross_by_op.items():
        op = s.scalars(
            select(FinancialOperation).where(FinancialOperation.external_ref == provider_ref)
        ).first()
        if op is None:
            open_case(
                s,
                dedupe_key=f"unknown-settlement:{report_ref}:{provider_ref}",
                case_type="settlement_for_unknown_payment",
                refs={"report_ref": report_ref, "operation_ref": provider_ref},
                difference_minor=gross,
            )
            continue
        refunded = s.scalar(
            select(func.coalesce(func.sum(FinancialOperation.amount_minor), 0)).where(
                FinancialOperation.parent_id == op.id,
                FinancialOperation.action == Action.REFUND,
                FinancialOperation.state == OpState.SUCCEEDED,
            )
        )
        expected = op.amount_minor - int(refunded)
        if gross != expected:  # T54: owned exception, no fudge entry
            open_case(
                s,
                dedupe_key=f"settlement-diff:{report_ref}:{provider_ref}",
                case_type="settlement_discrepancy",
                refs={
                    "report_ref": report_ref,
                    "operation_id": str(op.id),
                    "expected_minor": expected,
                    "reported_minor": gross,
                },
                difference_minor=gross - expected,
            )

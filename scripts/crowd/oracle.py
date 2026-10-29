"""After the crowd leaves: check the money and state invariants directly in the database.

These are the questions that matter regardless of what any single response said: was anyone
charged twice or more than they approved, refunded more than they paid, credited money that
never arrived; is the ledger balanced; does the provider agree with Trollie's records; are
holds, jobs or orders stuck.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.all_models import *  # noqa: F403 - register every table
from app.controls.models import Incident, KillSwitch
from app.durable.models import Job
from app.orders.models import Order, OrderLeg
from app.payments.models import Action, FinancialOperation, OpState, Refund, RefundState
from app.quotes.models import Quote
from app.simulators.models import SimMerchantReservation, SimMerchantStock, SimPayment
from app.wallet.models import Wallet
from app.wallet.service import balances

TERMINAL = {"COMPLETED", "CANCELLED", "EXPIRED", "PARTIAL", "DISPUTED"}
# Waiting on the customer (bank step not finished) is not stuck; it expires on its own.
WAITING = {"FULFILLING", "PAYMENT_PENDING"}
DEAD_REFUND = {RefundState.REJECTED_WITH_REASON, RefundState.FAILED_REQUIRES_ACTION}


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    severity: str = "critical"  # critical = money/authority; warning = operations


@dataclass
class OracleReport:
    checks: list[Check] = field(default_factory=list)
    facts: dict = field(default_factory=dict)

    def add(self, name, ok, detail, severity="critical"):
        self.checks.append(Check(name, bool(ok), detail, severity))


def audit(database_url: str, sent_by_account: dict[str, int], trial_balance: dict) -> OracleReport:
    rep = OracleReport()
    engine = create_engine(database_url)
    with Session(engine) as s:
        rep.add(
            "Ledger balanced",
            trial_balance.get("balanced"),
            f"debits {trial_balance.get('debits_minor')} = credits "
            f"{trial_balance.get('credits_minor')}; unbalanced txns "
            f"{len(trial_balance.get('unbalanced_transactions', []))}",
        )

        orders = list(s.scalars(select(Order)))
        quotes = {
            q.id: q
            for q in s.scalars(select(Quote).where(Quote.id.in_([o.quote_id for o in orders])))
        }
        ops = list(s.scalars(select(FinancialOperation)))
        refunds = list(s.scalars(select(Refund)))
        by_order = defaultdict(list)
        for op in ops:
            by_order[op.order_id].append(op)
        refunds_by_order = defaultdict(list)
        for r in refunds:
            refunds_by_order[r.order_id].append(r)

        over_charged, multi_capture, over_refund, leg_over = [], [], [], []
        for o in orders:
            total = quotes[o.quote_id].total_minor
            took = [
                op for op in by_order[o.id]
                if op.action in (Action.CAPTURE, Action.CHARGE) and op.state == OpState.SUCCEEDED
            ]  # fmt: skip
            charged = sum(op.amount_minor for op in took)
            if charged > total:
                over_charged.append(f"{o.id}: charged {charged} > approved {total}")
            if len(took) > 1:
                multi_capture.append(f"{o.id}: {len(took)} successful captures/charges")
            live = [r for r in refunds_by_order[o.id] if r.state not in DEAD_REFUND]
            refunded = sum(r.amount_minor for r in live)
            if not o.funding_source.startswith("wallet:") and refunded > charged:
                over_refund.append(f"{o.id}: refunds {refunded} > charged {charged}")
            per_leg = Counter()
            for r in live:
                for part in r.economic_allocation or []:
                    if part.get("leg_id"):
                        per_leg[part["leg_id"]] += part.get("amount_minor", 0)
            for leg in s.scalars(select(OrderLeg).where(OrderLeg.order_id == o.id)):
                cap = leg.goods_minor + leg.delivery_minor
                if per_leg[leg.leg_id] > cap:
                    leg_over.append(
                        f"order {str(o.id)[:8]} leg {leg.leg_id}: refunds {per_leg[leg.leg_id]} "
                        f"> leg value {cap}"
                    )
        rep.add("No order charged more than approved", not over_charged, _few(over_charged))
        rep.add("At most one capture/charge per order", not multi_capture, _few(multi_capture))
        rep.add("Refunds never exceed the charge", not over_refund, _few(over_refund))
        rep.add("Refunds per store leg never exceed that leg's value", not leg_over, _few(leg_over))

        # Provider vs Trollie: the same money moved on both sides.
        sim_rows = list(s.scalars(select(SimPayment)))
        sim_kinds = Counter(p.kind for p in sim_rows)
        sim_captured = sum(
            p.captured_minor
            if p.collection == "auth_capture"
            else (p.amount_minor if p.status == "succeeded" else 0)
            for p in sim_rows
            if p.kind == "checkout"
        )
        sim_refunded = sum(p.refunded_minor for p in sim_rows)
        ours_taken = sum(
            op.amount_minor
            for op in ops
            if op.action in (Action.CAPTURE, Action.CHARGE) and op.state == OpState.SUCCEEDED
        )
        ours_refunded = sum(
            r.amount_minor for r in refunds if r.state == RefundState.PROVIDER_CONFIRMED
        )
        rep.facts["provider_rows_by_kind"] = dict(sim_kinds)
        rep.facts["provider_captured_minor"] = sim_captured
        rep.facts["trollie_captured_minor"] = ours_taken
        rep.facts["provider_refunded_minor"] = sim_refunded
        rep.facts["trollie_refunds_confirmed_minor"] = ours_refunded
        rep.add(
            "Provider and Trollie agree on money taken",
            sim_captured == ours_taken,
            f"provider {sim_captured} vs Trollie {ours_taken}",
        )
        unknown = [op for op in ops if op.state in (OpState.UNKNOWN, OpState.RECONCILING)]
        rep.add(
            "No payment left in an unknown state",
            not unknown,
            _few([f"{op.action} {op.state} order {str(op.order_id)[:8]}" for op in unknown]),
            "warning",
        )

        # Wallets: never more than was actually confirmed into them; no negative balances.
        neg, overfull = [], []
        for w in s.scalars(select(Wallet)):
            b = balances(s, w.id)
            parts = [b["unallocated_minor"], b["reserved_minor"], b["frozen_minor"]]
            parts += list(b["envelopes_minor"].values())
            if any(x < 0 for x in parts):
                neg.append(f"wallet {str(w.id)[:8]}: {b}")
            sent = sent_by_account.get(str(w.account_id), 0)
            if b["total_minor"] > sent:
                overfull.append(f"wallet {str(w.id)[:8]}: holds {b['total_minor']} > sent {sent}")
        rep.add("No negative wallet or envelope balance", not neg, _few(neg))
        rep.add("No wallet holds more than was confirmed into it", not overfull, _few(overfull))

        # Stock and holds on the merchant side.
        bad_stock = list(
            s.scalars(
                select(SimMerchantStock).where(
                    (SimMerchantStock.held < 0)
                    | (SimMerchantStock.on_hand < 0)
                    | (SimMerchantStock.held > SimMerchantStock.on_hand)
                )
            )
        )
        rep.add(
            "Merchant stock never negative or over-held",
            not bad_stock,
            _few(
                [
                    f"{x.location_id}/{x.product_id}: on_hand {x.on_hand} held {x.held}"
                    for x in bad_stock
                ]
            ),
        )
        now = datetime.now(UTC)
        stale = s.scalar(
            select(func.count())
            .select_from(SimMerchantReservation)
            .where(SimMerchantReservation.state == "held", SimMerchantReservation.expires_at < now)
        )
        rep.add(
            "No merchant hold left past its expiry",
            stale == 0,
            f"{stale} expired holds still counted as held (stock locked up)",
            "warning",
        )

        states = Counter(o.state for o in orders)
        stuck = [o for o in orders if o.state not in TERMINAL | WAITING]
        rep.facts["orders_by_state"] = dict(states)
        rep.facts["attention_reasons"] = dict(
            Counter(o.attention_reason for o in orders if o.attention_reason)
        )
        rep.add(
            "No order stuck mid-flight",
            not stuck,
            _few([f"{str(o.id)[:8]} {o.state} {o.attention_reason or ''}" for o in stuck]),
            "warning",
        )
        # A paid order whose legs have all finished but which is still "fulfilling" with no
        # owner and no explanation is the silent failure customers experience as "ignored".
        orphaned = []
        for o in orders:
            if o.state != "FULFILLING" or o.attention_reason:
                continue
            leg_states = {
                leg.state for leg in s.scalars(select(OrderLeg).where(OrderLeg.order_id == o.id))
            }
            if leg_states and leg_states <= {"DELIVERED", "FAILED", "CANCELLED", "REJECTED"}:
                orphaned.append(f"{str(o.id)[:8]} legs {sorted(leg_states)}")
        rep.add(
            "No paid order left 'fulfilling' with nothing in flight", not orphaned, _few(orphaned)
        )
        dead = list(s.scalars(select(Job).where(Job.state == "dead")))
        rep.facts["dead_jobs"] = Counter(j.kind for j in dead)
        rep.add(
            "No job exhausted its retries",
            not dead,
            _few([f"{j.kind}: {getattr(j, 'last_error', '')}" for j in dead]),
            "warning",
        )
        rep.facts["incidents"] = dict(Counter(i.kind for i in s.scalars(select(Incident))))
        engaged = [k.scope for k in s.scalars(select(KillSwitch).where(KillSwitch.engaged))]
        rep.add("No kill switch engaged", not engaged, ", ".join(engaged) or "none", "warning")
        approvals_reused = s.execute(
            select(Order.approval_id, func.count())
            .where(Order.approval_id.is_not(None))
            .group_by(Order.approval_id)
            .having(func.count() > 1)
        ).all()
        rep.add(
            "Each approval used for at most one order", not approvals_reused, str(approvals_reused)
        )
    engine.dispose()
    return rep


def _few(items: list[str], n: int = 5) -> str:
    if not items:
        return "none"
    more = f" (+{len(items) - n} more)" if len(items) > n else ""
    return "; ".join(items[:n]) + more

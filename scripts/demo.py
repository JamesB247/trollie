"""Definition-of-done demo against a running server. SIMULATED — NOT REAL MONEY.

    uv run python -m scripts.demo                 # http://localhost:8000
    uv run python -m scripts.demo --base-url URL

Runs every scenario in CLAUDE.md "Definition of done" through the public API and the dev
harness, using a software passkey (the same ceremony the approval page performs in a
browser). Exits non-zero if any expectation fails. Time-dependent scenarios (holds expiring,
provider idempotency horizons) cannot be shown against a live clock; the report points to
the automated tests that cover them with a controllable clock.
"""

import argparse
import sys
import threading
import uuid
from dataclasses import dataclass, field

import httpx

from app.simulators.authenticator import SoftAuthenticator

TWO_STORE_LIST = [
    ("Sorghum meal", 1),
    ("Super maize meal", 1),
    ("Long grain rice", 1),
    ("Baked beans", 3),
    ("Chakalaka relish", 1),
]
SMALL_LIST = [
    ("Sorghum meal", 1),
    ("Super maize meal", 1),
    ("Baked beans", 3),
    ("Chakalaka relish", 1),
    ("Long grain rice", 1),
]


@dataclass
class Result:
    name: str
    ok: bool
    detail: str


@dataclass
class Demo:
    base: str
    http: httpx.Client = field(init=False)
    results: list[Result] = field(default_factory=list)
    products: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.http = httpx.Client(base_url=self.base, timeout=30)

    # --- plumbing --------------------------------------------------------------------

    def call(self, method, url, token=None, **kw):
        headers = kw.pop("headers", {})
        if token:
            headers["Authorization"] = f"Bearer {token}"
        r = self.http.request(method, url, headers=headers, **kw)
        return r

    def ok(self, method, url, token=None, **kw):
        r = self.call(method, url, token, **kw)
        if r.status_code >= 400:
            raise RuntimeError(f"{method} {url} -> {r.status_code}: {r.text}")
        return r.json()

    def check(self, name, condition, detail):
        self.results.append(Result(name, bool(condition), detail))

    def pump(self):
        self.ok("POST", "/v1/dev/pump")

    # --- actors ----------------------------------------------------------------------

    def customer(self):
        acct = self.ok("POST", "/v1/dev/accounts", json={"zone": "zone-a"})
        acct["auth"] = SoftAuthenticator()
        opts = self.ok("POST", "/v1/passkeys/registration-options", acct["token"])
        self.ok(
            "POST",
            "/v1/passkeys",
            acct["token"],
            json={
                "challenge_id": opts["challenge_id"],
                "credential": acct["auth"].register(opts["options"], self.base),
            },
        )
        if not self.products:
            for p in self.ok("GET", "/v1/catalogue/products", acct["token"]):
                self.products.setdefault(p["name"], p["product_id"])
        return acct

    def quote(self, who, items, funding, *, mode="complete_required", omissions=(), agent=None):
        sid = self.ok(
            "POST",
            "/v1/shopping-sessions",
            who["token"],
            json={"address_version_id": who["address_version_id"]},
        )["session_id"]
        for name, packs in items:  # the agent, if any, proposes the items
            self.ok(
                "POST",
                f"/v1/shopping-sessions/{sid}/items",
                agent or who["token"],
                json={
                    "line_id": name.lower().replace(" ", "-"),
                    "candidates": [{"product_id": self.products[name]}],
                    "quantity": {"packs": packs},
                },
            )
        est = self.ok("POST", f"/v1/shopping-sessions/{sid}/quotes", agent or who["token"], json={})
        estimate = est["options"]["cheapest"]
        if estimate is None:
            raise RuntimeError(f"no fulfilable basket: {est['blocking']}")
        if agent:
            self.ok("POST", "/v1/purchase-requests", agent, json={"quote_id": estimate["quote_id"]})
        return self.ok(
            "POST",
            f"/v1/quotes/{estimate['quote_id']}/firm",
            who["token"],
            json={
                "fulfilment_mode": mode,
                "permitted_omissions": list(omissions),
                "funding_source": funding,
            },
        )

    def approve(self, who, subject_type, subject_id):
        ch = self.ok(
            "POST",
            "/v1/approval-challenges",
            who["token"],
            json={"subject_type": subject_type, "subject_id": subject_id},
        )
        return self.ok(
            "POST",
            "/v1/approvals",
            who["token"],
            json={
                "challenge_id": ch["challenge_id"],
                "credential": who["auth"].assert_(ch["options"], self.base),
            },
        )["approval_id"]

    def order(self, who, quote, *, checkout=True):
        approval = self.approve(who, "quote", quote["quote_id"])
        order_id = self.ok(
            "POST",
            "/v1/orders",
            who["token"],
            json={"approval_id": approval},
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )["order_id"]
        ref = None
        if checkout:
            ref = self.ok("POST", f"/v1/orders/{order_id}/checkout-sessions", who["token"])[
                "checkout_ref"
            ]
        return order_id, ref

    def pay(self, ref, approve=True):
        self.ok("POST", f"/v1/dev/sim/checkouts/{ref}/complete", json={"approve": approve})

    def status(self, who, order_id):
        return self.ok("GET", f"/v1/orders/{order_id}", who["token"])

    def deliver(self, order_id):
        for leg in self.ok("GET", f"/v1/dev/orders/{order_id}/fulfilment")["legs"]:
            if leg["state"] != "ACCEPTED":
                continue
            self.ok("POST", f"/v1/dev/merchant/legs/{leg['order_leg_id']}/ready")
            self.ok("POST", f"/v1/dev/courier/jobs/{leg['delivery_job_id']}/collected")
            self.ok("POST", f"/v1/dev/courier/jobs/{leg['delivery_job_id']}/delivered")

    def fault(self, system, target, operation, mode, times=1):
        """Arm a simulator fault. Call after in-flight work has settled (see pump)."""
        self.ok(
            "POST",
            "/v1/dev/sim/faults",
            json={
                "system": system,
                "target": target,
                "operation": operation,
                "mode": mode,
                "times": times,
            },
        )

    def wallet(self, who, amount, *, deliveries=1):
        self.ok("POST", "/v1/wallet", who["token"])
        intent = self.ok("POST", "/v1/wallet/topups", who["token"], json={"amount_minor": amount})
        self.ok(
            "POST",
            "/v1/dev/sim/transfers",
            json={
                "transfer_ref": intent["transfer_ref"],
                "reference": intent["funding_reference"],
                "amount_minor": amount,
                "deliveries": deliveries,
            },
        )
        return intent

    # --- scenarios -------------------------------------------------------------------

    def pay_per_order(self, funding, label):
        who = self.customer()
        q = self.quote(who, TWO_STORE_LIST, funding)
        order_id, ref = self.order(who, q)
        self.pay(ref)
        st = self.status(who, order_id)
        self.check(
            f"{label}: paid and committed",
            st["state"] == "FULFILLING" and st["money"]["charged_minor"] == q["total_minor"],
            f"{len(q['legs'])} stores, R{q['total_minor'] / 100:.2f}, state {st['state']}",
        )
        self.deliver(order_id)
        st = self.status(who, order_id)
        self.check(f"{label}: delivered", st["state"] == "COMPLETED", f"state {st['state']}")

    def merchant_rejection(self, funding, label, expect):
        who = self.customer()
        q = self.quote(who, TWO_STORE_LIST, funding)
        self.fault("merchant", q["legs"][-1]["location_id"], "commit_order", "reject")
        order_id, ref = self.order(who, q)
        self.pay(ref)
        st = self.status(who, order_id)
        m = st["money"]
        if expect == "void":
            good = (
                st["state"] == "CANCELLED"
                and m["charged_minor"] == 0
                and (m["bank_hold_note"] == "hold release requested")
            )
            detail = f"no capture; {m['bank_hold_note']}"
        else:
            refunded = m["refund_requested_minor"] + m["refund_confirmed_minor"]
            good = st["state"] == "CANCELLED" and refunded == m["charged_minor"] > 0
            detail = f"charged R{m['charged_minor'] / 100:.2f}, refund R{refunded / 100:.2f}"
        self.check(f"{label}", good, detail)

    def payment_timeout(self):
        who = self.customer()
        q = self.quote(who, TWO_STORE_LIST, "pay_per_order:card_auth_capture")
        self.fault("payment", "create_checkout", "create_checkout", "timeout_after_effect")
        self.fault("payment", "capture", "capture", "timeout_after_effect")
        order_id, ref = self.order(who, q)
        self.pay(ref)
        st = self.status(who, order_id)
        self.check(
            "Payment timeouts: resolved by lookup, charged once",
            st["state"] == "FULFILLING" and st["money"]["charged_minor"] == q["total_minor"],
            f"charged R{st['money']['charged_minor'] / 100:.2f} of quote "
            f"R{q['total_minor'] / 100:.2f}",
        )

    def duplicate_webhook(self):
        who = self.customer()
        q = self.quote(who, TWO_STORE_LIST, "pay_per_order:card_auth_capture")
        self.fault("payment", "customer_completes", "customer_completes", "duplicate_webhook")
        order_id, ref = self.order(who, q)
        self.pay(ref)
        st = self.status(who, order_id)
        self.check(
            "Duplicate webhook: one economic effect",
            st["state"] == "FULFILLING" and st["money"]["charged_minor"] == q["total_minor"],
            f"state {st['state']}, charged once",
        )

    def wallet_flow(self):
        who = self.customer()
        self.wallet(who, 300_000, deliveries=2)  # the provider confirms the same top-up twice
        w = self.ok("GET", "/v1/wallet", who["token"])
        self.check(
            "Wallet: duplicate top-up event credits once",
            w["unallocated_minor"] == 300_000,
            f"unallocated R{w['unallocated_minor'] / 100:.2f}",
        )
        agent = self.ok("POST", "/v1/agents", who["token"], json={"name": "grocery agent"})
        self.ok(
            "POST",
            f"/v1/wallet/envelopes/{agent['envelope_id']}/allocations",
            who["token"],
            json={"amount_minor": 150_000},
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
        self.ok(
            "POST",
            f"/v1/agents/{agent['agent_id']}/grants",
            who["token"],
            json={
                "approval_mode": "per_quote",
                "address_version_id": who["address_version_id"],
                "per_order_cap_minor": 60_000,
                "period_cap_minor": 120_000,
            },
        )
        funding = f"wallet:envelope:{agent['envelope_id']}"
        q = self.quote(who, TWO_STORE_LIST, funding, agent=agent["agent_token"])
        order_id, _ = self.order(who, q, checkout=False)
        self.pump()
        st = self.status(who, order_id)
        w = self.ok("GET", "/v1/wallet", who["token"])
        self.check(
            "Wallet: agent-proposed basket approved by passkey, committed",
            st["state"] == "FULFILLING"
            and w["reserved_minor"] == 0
            and w["envelopes_minor"][agent["envelope_id"]] == 150_000 - q["total_minor"],
            f"{len(q['legs'])} stores, envelope now "
            f"R{w['envelopes_minor'][agent['envelope_id']] / 100:.2f}",
        )

        q2 = self.quote(who, SMALL_LIST, funding)
        self.fault("merchant", q2["legs"][0]["location_id"], "commit_order", "reject")
        order2, _ = self.order(who, q2, checkout=False)
        self.pump()
        st = self.status(who, order2)
        after = self.ok("GET", "/v1/wallet", who["token"])
        self.check(
            "Wallet: merchant refusal releases the hold",
            st["state"] == "CANCELLED"
            and after["reserved_minor"] == 0
            and after["envelopes_minor"] == w["envelopes_minor"],
            f"state {st['state']}, envelope unchanged",
        )

        intent = self.ok("POST", "/v1/wallet/topups", who["token"], json={"amount_minor": 5_000})
        self.ok(
            "POST",
            "/v1/dev/sim/transfers",
            json={
                "transfer_ref": intent["transfer_ref"],
                "reference": intent["funding_reference"],
                "amount_minor": 5_001,
            },
        )
        w2 = self.ok("GET", "/v1/wallet", who["token"])
        self.check(
            "Wallet: mismatched top-up goes to suspense, not the wallet",
            w2["unallocated_minor"] == after["unallocated_minor"],
            "amount differs from the intent by 1 cent",
        )

        # Concurrent spend on one envelope: two approved baskets, funds for only one.
        poor = self.customer()
        self.wallet(poor, 200_000)
        a2 = self.ok("POST", "/v1/agents", poor["token"], json={"name": "agent"})
        q_a = self.quote(poor, SMALL_LIST, "wallet:unallocated")
        q_b = self.quote(poor, SMALL_LIST, "wallet:unallocated")
        self.ok(
            "POST",
            f"/v1/wallet/envelopes/{a2['envelope_id']}/allocations",
            poor["token"],
            json={"amount_minor": 200_000 - q_a["total_minor"] - q_a["total_minor"] // 2},
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
        approvals = [self.approve(poor, "quote", q["quote_id"]) for q in (q_a, q_b)]
        codes: list[int] = []

        def place(approval_id):
            r = self.call(
                "POST",
                "/v1/orders",
                poor["token"],
                json={"approval_id": approval_id},
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
            codes.append(r.status_code)

        threads = [threading.Thread(target=place, args=(a,)) for a in approvals]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.check(
            "Wallet: concurrent spend cannot overdraw",
            sorted(codes) == [201, 422],
            f"responses {sorted(codes)}",
        )

        # Cancellation while a merchant commitment is uncertain: money stays held.
        self.pump()  # let in-flight orders settle so nothing else consumes the faults below
        q3 = self.quote(who, SMALL_LIST, funding)
        loc = q3["legs"][0]["location_id"]
        self.fault("merchant", loc, "commit_order", "timeout_after_effect")
        self.fault("merchant", loc, "get_order", "timeout_before_effect", times=100)
        order3, _ = self.order(who, q3, checkout=False)
        self.pump()
        self.ok("POST", f"/v1/orders/{order3}/cancellation-requests", who["token"])
        held = self.ok("GET", "/v1/wallet", who["token"])["reserved_minor"]
        self.ok("DELETE", "/v1/dev/sim/faults")
        self.pump()
        st = self.status(who, order3)
        final = self.ok("GET", "/v1/wallet", who["token"])
        self.check(
            "Wallet: cancellation race keeps money held until safe, then releases",
            held == q3["total_minor"]
            and st["state"] == "CANCELLED"
            and final["reserved_minor"] == 0,
            f"held R{held / 100:.2f} while uncertain, then {st['state']}",
        )

    def run(self) -> int:
        # The demo drives processing itself so injected faults hit the intended calls.
        self.ok("POST", "/v1/dev/worker", json={"paused": True})
        try:
            return self._run()
        finally:
            self.ok("POST", "/v1/dev/worker", json={"paused": False})

    def _run(self) -> int:
        self.ok("POST", "/v1/dev/seed")
        self.ok("DELETE", "/v1/dev/sim/faults")
        self.pump()
        self.pay_per_order("pay_per_order:card_auth_capture", "Card authorise/capture")
        self.pay_per_order("pay_per_order:immediate", "Immediate payment")
        self.merchant_rejection(
            "pay_per_order:card_auth_capture",
            "Card: merchant rejection before capture -> void",
            "void",
        )
        self.merchant_rejection(
            "pay_per_order:immediate",
            "Immediate: merchant rejection after payment -> refund",
            "refund",
        )
        self.payment_timeout()
        self.duplicate_webhook()
        self.wallet_flow()
        tb = self.ok("GET", "/v1/dev/ledger/trial-balance")
        self.check(
            "Ledger: every posted transaction balanced",
            tb["balanced"],
            f"debits R{tb['debits_minor'] / 100:,.2f} = credits R{tb['credits_minor'] / 100:,.2f}",
        )
        width = max(len(r.name) for r in self.results)
        print("\nTrollie definition-of-done demo — SIMULATED, NOT REAL MONEY\n")
        for r in self.results:
            print(f"  {'PASS' if r.ok else 'FAIL'}  {r.name:<{width}}  {r.detail}")
        print("\n  Covered by automated tests with a controllable clock (not shown live):")
        print("    hold expires during 3DS (T08), payment after hold expiry (T09),")
        print("    unknown state beyond the provider horizon (T27), settlement import (T53/T54).")
        failed = [r for r in self.results if not r.ok]
        print(f"\n  {len(self.results) - len(failed)}/{len(self.results)} checks passed")
        return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    sys.exit(Demo(parser.parse_args().base_url).run())


if __name__ == "__main__":
    main()

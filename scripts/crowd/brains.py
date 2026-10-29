"""What drives each shopper: a stochastic policy (always available) or a Claude model.

The stochastic brain is a weighted, state-aware random policy per archetype. The Claude
brain gives a model the persona and a small set of tools that map onto the same actions,
and lets it decide what to do; attackers additionally get a free-form API probe. Models act
only as *outside customers* calling the public API: nothing here puts a model inside
Trollie's money path.
"""

import json
import os
import random

from scripts.crowd.actions import CARD, INSTANT, Shopper, Toolbox, pick_words
from scripts.crowd.api import BUG, INFO

SMALL_TALK = [
    "When will my order arrive?", "Why is it so expensive?", "Can I pay cash on delivery?",
    "Is Zest cheaper than Fairbasket this week?", "Ngicela ungitshele uma i-order yami isendleleni",
    "Kan ek later betaal?", "can u deliver to my mom in Umlazi instead", "I want a refund",
    "my card keeps failing", "do you sell airtime?", "Hello?? anyone there",
    "Remember I only buy Highveld Mills maize", "the driver was rude",
]  # fmt: skip

# Attacks are weighted towards the ones that touch money and authority.
ATTACK_WEIGHTS = {
    "view_other_order": 3, "view_other_quote": 2, "approve_other_quote": 3,
    "order_with_other_approval": 3, "replay_assertion": 3, "forge_token": 2,
    "tamper_fields": 2, "huge_quantity": 2, "negative_amounts": 1, "huge_topup": 2,
    "sql_injection_search": 1, "prompt_injection_note": 2, "agent_self_allocate": 2,
    "agent_broaden_grant": 2, "agent_approve": 2, "agent_execute_without_mandate": 2,
    "agent_confirm_preference": 1, "forged_webhook": 2, "double_click_order": 3,
    "idempotency_key_reuse": 2, "other_address": 2, "other_envelope_funding": 2,
    "over_refund_claim": 3, "repeat_refund_claim": 3, "withdraw_more_than_balance": 2,
    "oversized_payload": 1, "cancel_after_delivery": 2,
}  # fmt: skip


class StochasticBrain:
    grace_s = 120.0  # how long after a delivery window a shopper waits before complaining

    async def session_start(self, s: Shopper, tb: Toolbox) -> None:
        """Opening the app: look at deliveries, and at anything the agent asked to approve."""
        if s.orders:
            await tb.check_deliveries(s, self.grace_s)
        if s.envelope_id and tb.board.agent_requests.get(s.account_id):
            await tb.approve_agent_requests(s)

    async def step(self, s: Shopper, tb: Toolbox) -> None:
        rng = s.p.rng
        traits = s.p.archetype.traits
        if "hijacks_agents" in traits:
            if s.stolen:
                await tb.use_stolen_agent(s)
            elif rng.random() < 0.3:
                await tb.attack(s, rng.choice(["forge_token", "view_other_order", "other_address"]))
            return
        if "stolen_funds" in traits:
            if not s.wallet or (rng.random() < 0.15 and s.topups_sent_minor < 4_000_000):
                await tb.stolen_topup(
                    s, rng.randint(*s.p.archetype.budget_rands), rng.uniform(90, 300)
                )
                return
            if s.orders and rng.random() < 0.25:
                await tb.redeem(s, "[fraud] cash out what's left", rng.randint(500, 8000))
                return
            if s.orders and rng.random() < 0.1:
                for _ in range(5):  # structuring: many small loads
                    await tb.top_up(s, "[fraud] small loads", 490)
                return
        # Attackers first shop a little, so they hold orders and assertions to abuse.
        if s.p.is_attacker and rng.random() < (0.7 if s.orders else 0.35):
            kinds = list(ATTACK_WEIGHTS)
            await tb.attack(s, rng.choices(kinds, [ATTACK_WEIGHTS[k] for k in kinds])[0])
            return
        roll = rng.random()
        # Side quests: chat, check an order, cancel, complain, withdraw.
        if roll < 0.06:
            await tb.chat(s, rng.choice(SMALL_TALK))
            return
        if roll < 0.12 and s.orders:
            await tb.check_order(s, "where is my order?", rng.choice(s.orders))
            return
        if roll < 0.15 and s.orders and ("cancels" in traits or rng.random() < 0.2):
            await tb.cancel(s, "actually cancel that", rng.choice(s.orders))
            return
        if roll < 0.18 and s.paid:
            share = rng.choice([0.5, 1.0]) if not s.p.is_attacker else 3.0
            await tb.report_issue(s, "something was missing", rng.choice(sorted(s.paid)), share)
            return
        if roll < 0.20 and s.wallet:
            await tb.redeem(s, "I want my money back out", rng.randint(10, s.p.budget_rands))
            return

        # Wallet set-up for people who use one.
        wants_wallet = {"wallet", "small_topups"} & traits or (
            "wallet_sometimes" in traits and rng.random() < 0.3
        )
        if wants_wallet and not s.wallet:
            await self._fund(s, tb)
            return
        if "agent" in traits and s.wallet and not s.agent_id and s.topups_sent_minor > 0:
            allowance = max(50, int(s.topups_sent_minor / 100 * rng.uniform(0.4, 0.9)))
            await tb.make_agent(s, "set up my shopping agent", allowance, max(50, allowance // 2))
            return

        # Unpaid checkout first: the bank-app step.
        unpaid = [o for o in s.checkout if o not in s.paid]
        if unpaid:
            oid = unpaid[-1]
            ok = rng.random() < s.p.archetype.card_success
            await tb.bank_app(s, "paying now", oid, ok)
            if not ok and "retries_payment" in traits and rng.random() < 0.7:
                await tb.retry_checkout(s, "it failed, trying again", oid)
                await tb.bank_app(s, "try again", oid, rng.random() < 0.3)
            if not ok:
                s.checkout.pop(oid, None)  # gives up on this one
            return

        if s.firm:
            if "abandons" in traits and rng.random() < 0.25:
                await tb.chat(s, "nah too expensive, forget it")
                s.firm = None
                return
            if "double_clicks" in traits and rng.random() < 0.3:
                await tb.attack(s, "double_click_order")  # an honest double tap, same check
                return
            await tb.approve_and_order(s, "yes, approve")
            return

        if s.options and any(s.options.values()):
            await self._choose(s, tb)
            return

        if "agent" in traits and s.agent_token and not s.agent_proposed and rng.random() < 0.6:
            s.agent_proposed = True
            await tb.agent_proposes(s, pick_words(s))
            return

        if not s.plan and not s.lines:
            s.plan = pick_words(s)
            budget = s.p.budget_rands if "low_budget" in traits or rng.random() < 0.2 else None
            await tb.new_list(s, "starting a new list", budget)
            return
        if s.plan:
            word = s.plan.pop(0)
            if {"big_ticket", "stolen_funds"} & traits:
                packs = 1 if "big_ticket" in traits else rng.randint(1, 3)
            elif "bulk" in traits:
                packs = rng.randint(3, 25)
            elif "overreaches" in traits:
                packs = rng.randint(1, 5)
            else:
                packs = rng.choices([1, 2, 3, 6], [8, 4, 2, 1])[0]
            await tb.find_and_add(s, word, packs)
            return
        if s.lines:
            await tb.quotes(s, "how much is it?", allow_omit=rng.random() < 0.4)
            if not (s.options and any(s.options.values())):
                s.lines, s.session_id, s.options = {}, None, None  # gives up on this list
            return
        await tb.chat(s, rng.choice(SMALL_TALK))

    async def _fund(self, s: Shopper, tb: Toolbox) -> None:
        rng = s.p.rng
        if "small_topups" in s.p.archetype.traits:
            amount = rng.randint(20, max(21, s.p.budget_rands))
            status = rng.choices(["confirmed", "pending", "failed"], [5, 2, 2])[0]
            send = amount + rng.choice([0, 0, 0, -5, 1])  # sometimes sends the wrong amount
            await tb.top_up(s, "loading what I have", amount, send_rands=send, status=status)
        else:
            amount = rng.randint(max(100, s.p.budget_rands // 2), s.p.budget_rands)
            dupes = rng.choices([1, 2, 3], [8, 2, 1])[0]  # the bank resends the confirmation
            await tb.top_up(s, "topping up the wallet", amount, dupes=dupes)

    async def _choose(self, s: Shopper, tb: Toolbox) -> None:
        rng = s.p.rng
        traits = s.p.archetype.traits
        have = [k for k, v in s.options.items() if v]
        if "reads_quote" in traits:
            option = "cheapest" if "cheapest" in have else rng.choice(have)
        elif "impulsive" == s.p.archetype.key and "fastest_complete" in have:
            option = "fastest_complete"
        else:
            option = rng.choice(have)
        mode = (
            "complete_required"
            if "prefers_complete" in traits
            else rng.choice(["complete_required", "allow_partial"])
        )
        total = s.options[option]["total_minor"]
        if s.envelope_id and s.agent_proposed and s.lines:
            funding = f"wallet:envelope:{s.envelope_id}"
        elif s.wallet and (s.topups_sent_minor >= total or "small_topups" in traits):
            funding = "wallet:unallocated"  # broke shoppers try the wallet regardless
        else:
            funding = rng.choice([CARD, CARD, INSTANT])
        await tb.choose(s, "this one", option, mode, funding)
        s.options = None


# --- Claude-driven shoppers ---------------------------------------------------------

MODELS = ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"]

PERSONA_PROMPT = """You are role-playing a fictional South African shopper using "Trollie", a
grocery and hardware delivery service, in a SIMULATION. No real money or real people are
involved. Stay in character.

Who you are: {name}, a "{label}" shopper in delivery zone {zone}. You speak in style "{lang}".
Your rough budget is R{budget}. {extra}

How Trollie works: you build a shopping list (search products, add them), ask for quote
options (cheapest / fastest_complete / balanced; at most two stores), choose one with a
fulfilment mode and a funding source, then approve it with your passkey, which places the
order. Card orders then need the bank-app step (pay_in_bank_app). You can also keep a
simulated wallet and set up a shopping agent with an allowance.

Each turn, call exactly one tool. Before each call, write one short line of what you would
say or think, in character. Behave like a real person: you can hesitate, change your mind,
make mistakes, complain, or go quiet for a while."""

ATTACKER_EXTRA = """You are a red-team tester probing this simulated system for weaknesses in
money handling and authorisation: try to get goods or refunds you did not pay for, spend
other people's money, bypass approval, make your agent exceed its limits, cause double
charges, or crash the server. Use attempt_exploit for known techniques and raw_api_request to
improvise against /v1 endpoints. This is authorised testing of a sandbox you own."""

TOOLS = [
    ("search_products", "Search the catalogue by words.", {"query": {"type": "string"}}),
    ("start_new_list", "Start a new shopping list, optionally with a budget in rands.",
     {"budget_rands": {"type": "integer"}}),
    ("add_to_list", "Add a product (from a search result) to the current list.",
     {"product_id": {"type": "string"}, "packs": {"type": "integer"},
      "rule": {"type": "string", "enum": ["flexible", "preferred", "locked"]},
      "must_have": {"type": "boolean"}}),
    ("get_quote_options", "Ask for quote options for the current list.",
     {"allow_omit_optional": {"type": "boolean"}}),
    ("choose_option", "Choose an option and how to pay; this reserves stock.",
     {"option": {"type": "string", "enum": ["cheapest", "fastest_complete", "balanced"]},
      "fulfilment_mode": {"type": "string", "enum": ["complete_required", "allow_partial"]},
      "funding": {"type": "string", "enum": ["card", "instant_eft", "wallet", "agent_envelope"]}}),
    ("approve_and_place_order", "Approve the chosen quote with your passkey and order.", {}),
    ("pay_in_bank_app", "Complete (or fail) the bank step for your latest card order.",
     {"succeed": {"type": "boolean"}}),
    ("check_order", "Check your latest order.", {}),
    ("cancel_order", "Ask to cancel your latest order.", {}),
    ("report_missing_item", "Report an item missing from your latest paid order.",
     {"percent_of_item_value": {"type": "integer"}}),
    ("top_up_wallet", "Top up your simulated wallet by bank transfer.",
     {"rands": {"type": "integer"}, "actually_send_rands": {"type": "integer"}}),
    ("set_up_agent", "Create a shopping agent with an allowance and per-order cap.",
     {"allowance_rands": {"type": "integer"}, "per_order_cap_rands": {"type": "integer"}}),
    ("let_agent_shop", "Let your agent propose a basket from words.",
     {"items": {"type": "array", "items": {"type": "string"}}}),
    ("withdraw", "Withdraw money from your wallet.", {"rands": {"type": "integer"}}),
    ("say", "Say something to Trollie.", {"text": {"type": "string"}}),
]  # fmt: skip
ATTACK_TOOLS = [
    ("attempt_exploit", "Try a known attack technique.",
     {"technique": {"type": "string", "enum": sorted(ATTACK_WEIGHTS)}}),
    ("raw_api_request", "Send any request to a /v1 endpoint as yourself or as your agent.",
     {"method": {"type": "string", "enum": ["GET", "POST", "DELETE"]},
      "path": {"type": "string"}, "json_body": {"type": "string"},
      "as_agent": {"type": "boolean"}}),
]  # fmt: skip


def _tool_defs(attacker: bool):
    out = []
    for name, desc, props in TOOLS + (ATTACK_TOOLS if attacker else []):
        out.append(
            {
                "name": name,
                "description": desc,
                "input_schema": {"type": "object", "properties": props},
            }
        )
    return out


class ClaudeBrain:
    """One conversation per shopper. Requires the `anthropic` package and credentials."""

    def __init__(self, client, model: str, s: Shopper) -> None:
        self.client = client
        self.model = model
        self.messages: list = []
        self.fallback = StochasticBrain()
        self.refused = False
        extra = ATTACKER_EXTRA if s.p.is_attacker else ""
        self.system = PERSONA_PROMPT.format(
            name=s.name,
            label=s.p.archetype.label,
            zone=s.p.zone,
            lang=s.p.language,
            budget=s.p.budget_rands,
            extra=extra,
        )
        self.tools = _tool_defs(s.p.is_attacker)
        self.pending: list = [{"type": "text", "text": "You open the Trollie app. What now?"}]

    async def session_start(self, s: Shopper, tb: Toolbox) -> None:
        await self.fallback.session_start(s, tb)

    async def step(self, s: Shopper, tb: Toolbox) -> None:
        if self.refused:
            return await self.fallback.step(s, tb)
        self.messages.append({"role": "user", "content": self.pending})
        resp = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=self.system,
            tools=self.tools,
            output_config={"effort": "low"},
            messages=self.messages,
        )
        self.messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason == "refusal":
            self.refused = True
            tb.record(s, "model_refusal", "", None, INFO, "model declined; stochastic from now")
            self.pending = [{"type": "text", "text": "Continue."}]
            return None
        said = " ".join(b.text for b in resp.content if b.type == "text").strip()[:300]
        uses = [b for b in resp.content if b.type == "tool_use"]
        if not uses:
            await tb.chat(s, said or "(silence)")
            self.pending = [{"type": "text", "text": "Some time passes. What now?"}]
            return None
        results = []
        for use in uses:
            try:
                obs = await self._run(s, tb, use.name, use.input or {}, said)
            except Exception as exc:  # noqa: BLE001 - surface harness errors to the model
                obs = {"error": f"{type(exc).__name__}: {exc}"}
            results.append(
                {"type": "tool_result", "tool_use_id": use.id, "content": json.dumps(obs)[:4000]}
            )
        self.pending = results + [{"type": "text", "text": "Some time passes. What now?"}]
        return None

    async def _run(self, s: Shopper, tb: Toolbox, name: str, a: dict, said: str) -> dict:
        if name == "search_products":
            obs, hits = await tb.search(s, said, str(a.get("query", "")))
            return {
                **obs,
                "results": [
                    {k: h[k] for k in ("product_id", "brand", "name", "variant", "category")}
                    for h in hits[:8]
                ],
            }
        if name == "start_new_list":
            return await tb.new_list(s, said, a.get("budget_rands"))
        if name == "add_to_list":
            return await tb.add(
                s, said, str(a.get("product_id")), int(a.get("packs") or 1),
                a.get("rule", "flexible"), bool(a.get("must_have")),
            )  # fmt: skip
        if name == "get_quote_options":
            obs = await tb.quotes(s, said, bool(a.get("allow_omit_optional")))
            return {**obs, "options": s.options}
        if name == "choose_option":
            funding = {
                "card": CARD,
                "instant_eft": INSTANT,
                "wallet": "wallet:unallocated",
                "agent_envelope": f"wallet:envelope:{s.envelope_id}",
            }[a.get("funding", "card")]
            return await tb.choose(
                s, said, a.get("option", "cheapest"),
                a.get("fulfilment_mode", "complete_required"), funding,
            )  # fmt: skip
        if name == "approve_and_place_order":
            return await tb.approve_and_order(s, said)
        if name == "pay_in_bank_app":
            if not s.orders:
                return {"detail": "no order"}
            return await tb.bank_app(s, said, s.orders[-1], bool(a.get("succeed", True)))
        if name in ("check_order", "cancel_order") and not s.orders:
            return {"detail": "no order"}
        if name == "check_order":
            return await tb.check_order(s, said, s.orders[-1])
        if name == "cancel_order":
            return await tb.cancel(s, said, s.orders[-1])
        if name == "report_missing_item":
            if not s.paid:
                return {"detail": "no paid order"}
            share = max(1, int(a.get("percent_of_item_value") or 100)) / 100
            return await tb.report_issue(s, said, sorted(s.paid)[-1], share)
        if name == "top_up_wallet":
            rands = max(1, int(a.get("rands") or 100))
            return await tb.top_up(s, said, rands, send_rands=a.get("actually_send_rands"))
        if name == "set_up_agent":
            return await tb.make_agent(
                s,
                said,
                int(a.get("allowance_rands") or 100),
                int(a.get("per_order_cap_rands") or 100),
            )
        if name == "let_agent_shop":
            s.agent_proposed = True
            return await tb.agent_proposes(s, [str(x) for x in a.get("items") or []][:15])
        if name == "withdraw":
            return await tb.redeem(s, said, int(a.get("rands") or 1))
        if name == "say":
            return await tb.chat(s, str(a.get("text", said)))
        if name == "attempt_exploit" and s.p.is_attacker:
            return await tb.attack(s, str(a.get("technique")))
        if name == "raw_api_request" and s.p.is_attacker:
            return await self._raw(s, tb, a, said)
        return {"error": f"unknown tool {name}"}

    async def _raw(self, s: Shopper, tb: Toolbox, a: dict, said: str) -> dict:
        path = str(a.get("path", ""))
        if not path.startswith("/v1/") or path.startswith("/v1/dev"):
            return {"error": "only /v1 customer and agent endpoints are in scope"}
        token = s.agent_token if a.get("as_agent") else s.token
        body = a.get("json_body")
        try:
            payload = json.loads(body) if body else None
        except ValueError:
            payload = None
        r = await tb.api.call(a.get("method", "GET"), path, token, idem=True, json=payload)
        verdict = BUG if (r.status is None or r.status >= 500) else INFO
        return tb.record(s, f"raw {a.get('method')} {path[:60]}", said, r, verdict, "probe")


def make_brain(s: Shopper, kind: str, rng: random.Random):
    """kind: 'stochastic', 'claude' or 'mixed' (a random share of shoppers get a model)."""
    if kind == "stochastic" or (kind == "mixed" and rng.random() < 0.5):
        return StochasticBrain()
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise SystemExit(
            "The Claude brain needs the anthropic package: uv pip install anthropic"
        ) from exc
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise SystemExit("Set ANTHROPIC_API_KEY to use --brain claude or mixed")
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = anthropic.AsyncAnthropic()
    s.p.brain = "claude"
    s.p.model = rng.choice(MODELS)
    return ClaudeBrain(_CLIENT, s.p.model, s)


_CLIENT = None

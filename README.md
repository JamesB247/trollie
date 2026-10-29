# Trollie

Multi-retailer purchasing and fulfilment for South African households: one list → a complete,
fulfilable basket from at most two stores → explicit, passkey-bound approval of an immutable
quote → orders placed with each store → deliveries coordinated → ledger reconciled.

**This build is a synthetic sandbox. SIMULATED — NOT REAL MONEY.** All merchants, brands,
couriers and payment providers are fictional simulators. There are no real deposits,
payouts, merchants, WhatsApp or LLM calls, and the app refuses to start in a live
configuration.

## Documents

Start with `CLAUDE.md` (sprint scope and rules), then `DECISIONS.md` (adopted decisions,
superseded clauses, implementation choices).

- `docs/ENGINEERING_BLUEPRINT.md` — implementation spec (wins on technical matters, except
  clauses superseded in `DECISIONS.md`)
- `docs/PRD.md` — product requirements v2.2
- `docs/WALLET_AND_SPRINT_DECISIONS_ADDENDUM.md` — wallet scope addendum, adopted with A1–A6
- `docs/ACCEPTANCE_STATUS.md` — T01–T60 and W01–W20 with evidence and honest limits
- `docs/CROWD_SIMULATION.md` — 60 random shoppers (honest, broke, hostile) against a fictional
  multi-region market: how to run it, what broke, what was fixed

Current sprint: M0 baseline + M2–M3 synthetic commerce + W1–W3 synthetic wallet. M1
commercial feasibility (signed merchants, provider topology, courier terms) remains open.

## Run it

```bash
docker compose up --build
```

Then open http://localhost:8000/healthz. Use `localhost`, not `127.0.0.1`: passkeys are bound
to the origin `http://localhost:8000`.

Run the definition-of-done scenarios against the running stack (needs `uv` on the host):

```bash
uv sync
uv run python -m scripts.demo
```

It seeds the fictional stores and runs: card and instant-payment purchases across two stores
through delivery; merchant rejection (void before capture, refund after payment); payment
timeouts; a duplicate webhook; wallet funding with a duplicate event; an agent-proposed
basket approved by passkey; merchant refusal; a mismatched top-up; concurrent spend; a
cancellation racing an uncertain merchant; and a balanced ledger.

### Try the approval page yourself

```bash
curl -s -X POST localhost:8000/v1/dev/seed
curl -s -X POST localhost:8000/v1/dev/accounts -H 'content-type: application/json' -d '{}'
```

Open the returned `login_url` in a browser, then build a quote via the API (see
`tests/test_api.py::test_full_card_purchase_over_http` for the calls) and open
`/approve/quote/<quote_id>`. The page lets you create a passkey, approve, place the order and
complete the simulated payment step. `/merchant` is the merchant/courier harness and
`/wallet` shows simulated balances.

## Develop without Docker

Needs Postgres 16 with a `trollie` role and `trollie` / `trollie_test` databases.

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:create_app --factory --port 8000
```

```bash
uv run pytest
```

```bash
uv run python -m scripts.acceptance_report
```

`HYPOTHESIS_PROFILE=thorough uv run pytest` runs the property tests (including the optimiser
brute-force oracle) for 5 000 examples each. The browser test needs Node with Playwright and
is skipped otherwise.

## Layout

`app/` is a modular monolith with one package per bounded context: `products`, `offers`,
`merchants`, `quotes` (optimiser, quotes), `approvals` (WebAuthn), `orders` (orchestration,
state machines), `payments` (capability profiles, financial executor, refunds, settlement),
`wallet`, `delivery`, `ledger`, `durable` (idempotency, outbox, inbox, jobs),
`reconciliation`, `controls` (kill switches, incidents, audit), `accounts`, `support`,
`simulators` (merchant, payment provider, courier, software passkey) and `api`.

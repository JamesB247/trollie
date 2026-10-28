# Trollie — build brief for Claude Code

Read this first. It tells you what to build **now**, which documents govern, and what is out of scope.

## Documents and precedence

1. `docs/ENGINEERING_BLUEPRINT.md` — the implementation spec. Schema, state machines, API contracts, compensation matrix, monetary invariants, 60 acceptance tests (T01–T60), milestones M0–M8. **Wins on anything technical.**
2. `docs/PRD.md` — product context: positioning, customer promise, preferences model, partial-fulfilment rules, phasing, decision IDs (D01–D10). Use for intent and wording; defer to the blueprint on mechanics.
3. This file — scope for the current sprint.

If the two documents disagree, the blueprint wins. If this file disagrees with either, this file wins for scope only; never for correctness rules.

## What Trollie is

A multi-retailer purchasing and fulfilment service for South African households. One shopping list → deterministic optimiser builds a complete, fulfilable basket from participating stores (max two) → customer explicitly approves an immutable quote → orders placed with each retailer → deliveries coordinated → ledger reconciled. The customer keeps control of payment. No stored-value wallet.

Core engine principle: **find the cheapest successfully fulfilable basket that satisfies the customer's preferences, delivery requirements and approved budget** — not the cheapest set of listed prices.

## Scope for this sprint: milestones M0–M3 only

Build the commerce spine with synthetic data. No real money, no real merchants, no WhatsApp, no LLM in the money path.

**In scope**
- Modular monolith: Python 3.12, FastAPI, PostgreSQL. Integer cents, UTC timestamps, UUIDs. No floats for money. No Redis.
- Three or four clearly fictional merchants with labelled synthetic catalogues and stock (no real retailer names or logos).
- Product/offer model: canonical products separate from per-store offers (blueprint §7). Matching hierarchy: verified GTIN → verified mapping → exact attributes → user-confirmed similarity.
- Deterministic optimiser (blueprint §11): enumeration/IP over store sets, max two stores, VAT-inclusive totals, delivery per leg, promotions, minimums; outputs cheapest / fastest-complete / balanced; names the blocking constraint instead of shrinking quantities.
- Preferences as hard rules: Locked / Preferred / Flexible, per-item must-have, complete-required vs allow-partial (PRD "Partial-fulfilment rules"; blueprint §5.4 decision table).
- Immutable quote snapshots with canonical hash and expiry (blueprint §5.2, §10.4).
- Approval binding: single-use server challenge bound to the quote hash; WebAuthn verification via a maintained library (blueprint §13.1). Any material change invalidates approval.
- Merchant reservation object with expiry and release semantics (blueprint §2.5, §8.1).
- Purchase/leg/payment/delivery/refund state machines exactly as blueprint §8, with a **simulated** payment adapter that implements both branches (authorise/capture and immediate payment) and can be told to time out, duplicate, or arrive late.
- Transactional outbox + verified event inbox; business-operation idempotency keys (reuse with changed payload → conflict).
- Double-entry ledger with the monetary invariants in blueprint §7.3 enforced in a posting procedure; append-only; balances derived from entries.
- Compensation matrix (blueprint §9.5) implemented for the simulated adapter.
- Internal API per blueprint §10 (customer, agent, merchant contract, financial commands, structured error codes).
- A minimal mobile-web approval page rendered from authoritative server data. No native app.

**Tests that must pass before you call this sprint done**
- T01–T30 and T45–T54 from the blueprint §17, as automated tests with deterministic fixtures and fault injection.
- Property-based tests for ledger balance, caps, quote transformations and state transitions.
- Known-answer optimiser fixtures checked against a brute-force oracle on small instances.

**Out of scope — do not build, do not stub as if it worked**
- Real payment providers (Stitch, Ozow, Peach, Yoco). Write the adapter interface and the simulated adapter only.
- WhatsApp, voice notes, multilingual extraction, any LLM call. The "agent" is a structured-intent fixture for now.
- Stored-value wallet, envelopes as real reservations, standing mandates/auto-approve, virtual cards, QR payments, external third-party agents, MCP server, Retailer Connect API, B2B replenishment, credit, township collection points.
- Real courier integrations. Delivery is a simulated adapter with capacity, windows and failure injection.
- KYC/CDD vendors. Account model only.
- AWS deployment, Cloudflare, KMS. Local Docker Compose is enough.

If a feature is listed above as out of scope, leave a clearly named extension point and a TODO referencing the blueprint section. Do not fake it.

## Rules that are not negotiable

- The model/agent layer can **propose** a structured intent referencing existing identifiers. It can never supply prices, payees, addresses, URLs, or mark anything approved. No code path from an agent call to authorised spend.
- One economic effect per intended operation. Unknown payment state is reconciled before any retry; never issue a fresh idempotency key because a user clicked again.
- Posted ledger entries are never updated or deleted. Corrections are reversing entries.
- A must-have item overrides allow-partial. Money freed by a removal is not consent to add, swap or upgrade anything.
- A new merchant, new item, quantity increase, higher fee, extra delivery leg or later window always needs a fresh quote and approval.
- Nothing in merchant-supplied content (product descriptions, notes, webhook payloads) can change a payee, address, total or permission.
- Secrets never in code. Logs redact anything resembling PAN/CVV/ID numbers even though none should exist yet.

## Conventions

- Layout: `app/` (modules by bounded context: products, offers, quotes, approvals, orders, payments, delivery, ledger, reconciliation, support), `tests/`, `migrations/`, `docs/`, `scripts/`.
- Migrations with Alembic. Row locking or serializable transactions for reservations and limit counters.
- Provider calls happen outside DB transactions: persist intent → call → persist observed result.
- Keep a `DECISIONS.md` log: when you make a choice the documents leave open, record it with the relevant D-number from the PRD.
- Commit small. Every PR names the blueprint section and the tests it satisfies.

## Definition of done for M0–M3

A developer can run `docker compose up`, seed the synthetic merchants, submit a list via the API, receive quote options, approve one through the web page with a passkey, watch the simulated payment and merchant commitments complete, and see a balanced ledger and reconciled state — and then re-run the same flow with an injected merchant rejection, a payment timeout and a duplicate webhook, and watch the system refuse to double-charge or over-deliver.

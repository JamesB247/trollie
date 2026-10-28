# Trollie — build brief for Claude Code

Read this first. It tells you what to build **now**, which documents govern, and what is out of scope.

## Documents and precedence

1. `docs/ENGINEERING_BLUEPRINT.md` — the implementation spec. Schema, state machines, API contracts, compensation matrix, monetary invariants, 60 acceptance tests (T01–T60), milestones M0–M8. **Wins on anything technical**, except clauses explicitly superseded in `DECISIONS.md`.
2. `DECISIONS.md` — adopted decisions and the exact clauses they supersede. Includes the adopted wallet addendum (`docs/WALLET_AND_SPRINT_DECISIONS_ADDENDUM.md`) with builder amendments A1–A6; where they differ, the amendment wins.
3. `docs/PRD.md` — product context: positioning, customer promise, preferences model, partial-fulfilment rules, phasing, decision IDs (D01–D10). Use for intent and wording; defer to the blueprint on mechanics.
4. This file — scope for the current sprint.

If the documents disagree, the blueprint wins unless `DECISIONS.md` records a superseded clause. If this file disagrees with any of them, this file wins for scope only; never for correctness rules. A scope addition never relaxes an approval, privacy, reconciliation or money-integrity control.

## What Trollie is

A multi-retailer purchasing and fulfilment service for South African households. One shopping list → deterministic optimiser builds a complete, fulfilable basket from participating stores (max two) → customer explicitly approves an immutable quote → orders placed with each retailer → deliveries coordinated → ledger reconciled.

A purchase is funded either **per order** through a payment provider, or from a **customer-owned wallet** with agent-specific envelopes and scoped, revocable spending grants. In this sprint both are simulated. No real customer money is received or held.

Core engine principle: **find the cheapest successfully fulfilable basket that satisfies the customer's preferences, delivery requirements and approved budget** — not the cheapest set of listed prices.

## Scope for this sprint

**M0 baseline work + M2–M3 synthetic commerce build + W1–W3 synthetic wallet extension. M1 commercial feasibility remains open** and cannot be completed by code (DECISIONS.md D-S01).

Synthetic data only. No real money, no real merchants, no WhatsApp, no LLM in the money path. Build order: shared core → pay-per-order → wallet (DECISIONS.md A6).

**In scope — commerce spine (M2–M3)**
- Modular monolith: Python 3.12, FastAPI, PostgreSQL. Integer cents, UTC timestamps, UUIDs. No floats for money. No Redis.
- Three or four clearly fictional merchants with labelled synthetic catalogues and stock (no real retailer names or logos).
- Product/offer model: canonical products separate from per-store offers (blueprint §7). Matching hierarchy: verified GTIN → verified mapping → exact attributes → user-confirmed similarity.
- Deterministic optimiser (blueprint §11; DECISIONS.md D-S03.1): enumeration/IP over store sets, max two stores, VAT-inclusive totals, delivery per leg, structured promotions (D-S03.3), minimums; outputs `cheapest` / `fastest_complete` / `balanced`; names the blocking constraint instead of shrinking quantities.
- Preferences as hard rules: Locked / Preferred / Flexible, per-item must-have, complete-required vs allow-partial (PRD "Partial-fulfilment rules"; blueprint §5.4 decision table).
- Immutable quote snapshots with canonical hash and expiry (blueprint §5.2, §10.4). The funding source is part of the hashed snapshot (A4).
- Approval binding: single-use server challenge bound to the quote hash; WebAuthn verification via a maintained library (blueprint §13.1; D-S03.6). Any material change invalidates approval.
- Merchant reservation object with expiry and release semantics (blueprint §2.5, §8.1).
- Purchase/leg/payment/delivery/refund state machines exactly as blueprint §8, with a **simulated** payment adapter that implements both branches (authorise/capture and immediate payment) and can be told to time out, duplicate, or arrive late.
- Versioned simulated provider capability profiles, including one restrictive profile; unsupported combinations fail closed (blueprint §4.1; D-S03.7).
- Transactional outbox + verified event inbox; business-operation idempotency keys (reuse with changed payload → conflict). Postgres-backed job queue (D-S03.4).
- Double-entry ledger with the monetary invariants in blueprint §7.3 enforced in a posting procedure; append-only; balances derived from entries. Synthetic subledger per D-S03.2.
- Compensation matrix (blueprint §9.5) implemented for the simulated adapters.
- Internal API per blueprint §10 (customer, agent, merchant contract, financial commands, structured error codes).
- A minimal mobile-web approval page rendered from authoritative server data, and a thin local merchant page or CLI harness for accept/reject/ready (D-S04). No native app.
- Address encryption via local AES-256-GCM provider (D-S03.5); fictional addresses only.

**In scope — synthetic wallet (W1–W3; DECISIONS.md D-W01–D-W03, A2–A5)**
- W1: simulated top-up intents and evidence, unmatched-funds suspense, customer-owned wallet, exclusive agent envelopes, ownership invariants.
- W2: wallet-funded purchases reusing the same quote, approval, ledger and orchestration — reserve, commit, release, refund (A5) and redemption *state*.
- W3: scoped revocable grants; a bounded mandate fixture approved by passkey and off by default (A2); concurrency, revocation, top-up reversal and crash recovery.
- Wallet UI showing total, available, allocated, reserved and pending. Every wallet amount is labelled **SIMULATED — NOT REAL MONEY**.

**Tests that must pass before you call this sprint done**
- T01–T40 and T45–T54 from blueprint §17, plus the approved-address control from T42, as automated tests with deterministic fixtures and fault injection.
- W01–W20 from the addendum §8, with W05 as amended (A3).
- Every test records a status from the taxonomy in DECISIONS.md (D-S02). Tests that a fixture cannot honestly prove (e.g. T03 real OCR, T22 real PIN device, T46 production egress) are marked as such, never shown as fully passed.
- Property-based tests for ledger balance, caps, quote transformations, state transitions and envelope/grant arithmetic.
- Known-answer optimiser fixtures checked against a brute-force oracle on small instances.

**Out of scope — do not build, do not stub as if it worked**
- Real payment providers (Stitch, Ozow, Peach, Yoco). Write the adapter interface and the simulated adapter only.
- Real deposits, custody, live wallet-funded purchases, real withdrawals/payouts, unrestricted autonomous spending. Startup refuses live credentials/endpoints and refuses a synthetic database under a live runtime (W20).
- WhatsApp, voice notes, multilingual extraction, any LLM call. The "agent" is a structured-intent fixture for now.
- Virtual cards, QR payments, external third-party agents, MCP server, Retailer Connect API, B2B replenishment, credit, township collection points.
- Real courier integrations. Delivery is a simulated adapter with capacity, windows and failure injection. Consolidated pickup disabled by default.
- KYC/CDD vendors. Account model only.
- AWS deployment, Cloudflare, KMS. Local Docker Compose is enough.

If a feature is listed above as out of scope, leave a clearly named extension point and a TODO referencing the blueprint section. Do not fake it.

## Rules that are not negotiable

- The model/agent layer can **propose** a structured intent referencing existing identifiers. It can never supply prices, payees, addresses, URLs, or mark anything approved. No agent call results in spend without an owner-signed authority — a quote-bound approval or a versioned, passkey-approved mandate — verified by the trusted executor.
- An agent can never allocate funds to itself, broaden its grant, change a destination or revoke another party's controls. Only the owner can broaden a grant.
- Wallet funding is not purchase consent. Pending, disputed or unverified funds are never spendable.
- One economic effect per intended operation. Unknown payment state is reconciled before any retry; never issue a fresh idempotency key because a user clicked again.
- Posted ledger entries are never updated or deleted. Corrections are reversing entries. No editable balance store outside the ledger.
- A must-have item overrides allow-partial. Money freed by a removal is not consent to add, swap or upgrade anything.
- A new merchant, new item, quantity increase, higher fee, extra delivery leg, later window or different funding source always needs a fresh quote and approval.
- Refunds never restore grant spending or velocity limits.
- Nothing in merchant-supplied content (product descriptions, notes, webhook payloads) can change a payee, address, total or permission.
- Secrets never in code. Logs redact anything resembling PAN/CVV/ID numbers even though none should exist yet.

## Conventions

- Layout: `app/` (modules by bounded context: products, offers, quotes, approvals, orders, payments, wallet, delivery, ledger, reconciliation, support), `tests/`, `migrations/`, `docs/`, `scripts/`.
- Migrations with Alembic. Row locking or serializable transactions for reservations, envelopes and limit counters.
- Provider calls happen outside DB transactions: persist intent → call → persist observed result.
- Keep `DECISIONS.md`: when you make a choice the documents leave open, add a row under "Implementation decisions" with the relevant D-number.
- Commit small. Every PR names the blueprint section and the tests it satisfies.

## Definition of done

Without external live services, a developer can run `docker compose up`, seed the synthetic merchants and:

1. **Pay per order:** submit a list via the API, receive quote options, approve one through the web page with a passkey, watch the simulated payment and merchant commitments complete, and see a balanced ledger and reconciled state. Do this on both simulated rails (authorise/capture and immediate payment). Re-run with an injected merchant rejection (before capture → void; after immediate payment → refund), a payment timeout and a duplicate webhook, and watch the system refuse to double-charge or over-deliver.
2. **Wallet:** fund a simulated wallet (a duplicate event does not double-credit), allocate an exclusive agent envelope with a scoped grant, have the agent fixture propose a two-store basket, approve it by passkey (or via the separately flagged mandate fixture), and see funds reserved, merchants committed, delivery simulated and settlement reconciled. Re-run with a merchant refusal, top-up mismatch, expired reservation, unknown settlement, cancellation race, duplicate webhook and concurrent spend on one envelope; each yields the expected control and compensation outcome.
3. Postgres restarts and worker crashes neither create money nor lose obligations. Every posted journal stays balanced.
4. Test output separates simulated/domain/browser evidence from outstanding real-provider, real-device and operational evidence.

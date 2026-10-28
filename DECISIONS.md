# Trollie — Decision log

Decisions the governing documents leave open, or that change them. Each entry records: ID, status, owner role, options, chosen option, evidence, date, review trigger, affected requirements and any **superseded clauses** (quoted exactly).

PRD decision IDs D01–D10 (blueprint §3.2) remain **open** unless an entry below says otherwise. Nothing in this file closes a legal, provider, merchant or courier gate; those need their own evidence.

Sources:
- **BP** — `docs/ENGINEERING_BLUEPRINT.md` v1.0
- **PRD** — `docs/PRD.md` v2.1 (amended to v2.2 by this log)
- **ADD** — `docs/WALLET_AND_SPRINT_DECISIONS_ADDENDUM.md` (proposed 2026-10-28)
- **BR** — builder review of ADD, 2026-10-28 (amendments A1–A6 below)

---

## Adoption record — 2026-10-28

**Founder decision (2026-10-28):** adopt ADD with builder amendments A1–A6.

Adopted: D-W01, D-W02, D-W03, D-S01, D-S02, D-S03 (§9.1–§9.7), D-S04, D-S05, D-S06 as written in ADD, except where an amendment below changes them. Where ADD and an amendment differ, the amendment wins.

ADD does **not** relax any approval, privacy, reconciliation or money-integrity control in BP. Where ADD is silent, BP still governs.

### Superseded clauses

| Document | Clause (exact text) | Replaced by |
|---|---|---|
| BP §3.1 | `\| Wallet \| None \| Existing requirement \|` | Synthetic wallet module in scope (D-W01–W03); live stored value still gated |
| CLAUDE.md, "What Trollie is" | "The customer keeps control of payment. No stored-value wallet." | Customer funds a **simulated** wallet or pays per order; no live stored value |
| CLAUDE.md, out of scope | "Stored-value wallet, envelopes as real reservations, standing mandates/auto-approve, …" | Synthetic wallet, envelopes and bounded mandate fixture in scope; real deposits/custody/withdrawals remain out |
| CLAUDE.md, non-negotiable rules | "No code path from an agent call to authorised spend." | "No agent call results in spend without an owner-signed authority — a quote-bound approval or a versioned, passkey-approved mandate — verified by the trusted executor." (A2) |
| CLAUDE.md, scope heading | "milestones M0–M3 only" | "M0 baseline + M2–M3 synthetic commerce + W1–W3 synthetic wallet; M1 open" (D-S01) |
| CLAUDE.md, tests | "T01–T30 and T45–T54" | Adds T31–T40, T42 address control, W01–W20; status taxonomy (D-S02) |
| CLAUDE.md, definition of done | M0–M3 paragraph | Revised DoD covering both funding sources (A1) |
| PRD, Future purchases | "until the wallet gate clears, an envelope is a planning budget, not reserved money" | Applies to **live** money; synthetic envelopes are real reservations in the simulator |

---

## Builder amendments to ADD

### A1 — Definition of done covers both funding sources
**Problem:** ADD §13 demonstrates only wallet-funded purchases. Pay-per-order (card authorise/capture, immediate payment) remains a funding source (ADD §5) and BP §9.2–9.3 branches are still in scope.
**Decision:** DoD demonstrates (a) pay-per-order on both simulated rails, including payment timeout, duplicate webhook and merchant rejection before capture (void) and after immediate payment (refund); and (b) the wallet flow in ADD §13.
**Affects:** CLAUDE.md DoD; T08, T09, T26, T28, T37, T38, T39.

### A2 — Mandate approval and execution
**Problem:** ADD §6 does not say how a mandate is approved, and conflicts literally with CLAUDE.md's "no code path from an agent call to authorised spend".
**Decision:**
1. A mandate is an immutable, versioned record with a canonical hash. It becomes active only through the same WebAuthn ceremony as quote approval: single-use challenge bound to the mandate hash, user verification required. Any change is a new version needing a new ceremony.
2. Mandate execution is **off by default**. It is enabled only by `TROLLIE_MANDATE_FIXTURE_ENABLED=true` **and** `TROLLIE_ENV=test`. Any other combination with the flag set refuses to start.
3. Every mandate purchase still produces an immutable quote. The trusted executor checks the quote against the mandate (merchant set, address version, items/categories, per-order cap, period cap, velocity, validity window, revocation state) under lock before reserving funds. The agent can request execution; it cannot sign, approve or post.
4. Non-negotiable rule reworded as in the superseded-clauses table.
**Affects:** W06, W08, W09, W15, W18; T18, T20, T21.

### A3 — W05 tests the real race
**Problem:** with exclusive envelopes, two agents spending their own allocations never contend for the same money.
**Decision:** W05 becomes "**Concurrent spend on one envelope**": (a) one agent submits two reservations concurrently that together exceed the envelope; (b) an agent reserves while the owner de-allocates from that envelope; (c) an agent reserves while the owner redeems unallocated plus de-allocated funds. Invariant: no overspend, no double use, available ≥ 0 at every committed state. A separate test keeps two agents on separate envelopes to prove isolation (no cross-envelope draw).
**Affects:** W05, W14.

### A4 — Funding source for owner-approved purchases
**Problem:** ADD does not say what funds a purchase the owner approves directly.
**Decision:** the funding source is part of the quote's payment constraints (BP §5.2 "Payment product/method constraints") and is covered by the quote hash. Options: `pay_per_order:<rail>`, `wallet:unallocated`, `wallet:envelope:<id>`. The owner may approve from unallocated funds or any of their envelopes. An agent may only use its own envelope under its active grant. Changing the funding source is a material change requiring a new quote version and approval.
**Affects:** quote snapshot schema; W06, W07, W16.

### A5 — Refund destination for wallet-funded purchases
**Decision:**
- Refund of a wallet-funded purchase restores money to the **envelope it was drawn from** if that envelope still exists and its grant is active; otherwise to **owner unallocated**. The ledger records which.
- Refunds never restore grant counters (per-period cumulative spend, velocity). Money and authority counters are separate (ADD §6).
- Pay-per-order refunds go to the original payment reference only; never forced into wallet credit (ADD §5).
**Affects:** W12, W18; T33, T34.

### A6 — Build sequencing
**Decision:** build in this order on one ledger:
1. Shared core — schema, ledger posting procedure, outbox/inbox, idempotent financial operations, products/offers, optimiser, quotes, approval ceremony.
2. Pay-per-order funding source on the simulated payment adapter (both rails), merchant and delivery simulators, compensation matrix.
3. Wallet funding source (W1 → W2 → W3) reusing the same quote, approval, ledger and orchestration.
No parallel or editable balance store at any stage.

---

## Day-one defaults (ADD §9, adopted)

| ID | Decision | Notes |
|---|---|---|
| D-S03.1 | Strategies `cheapest`, `fastest_complete`, `balanced`. Balanced = min delivered total among feasible candidates completing by `min(customer_deadline, t_fastest + 30 min)`. Ties: fewer legs → earlier completion → stable offer IDs. | Policy versioned (`balanced-v1`) and shown in UI and quote. Synthetic default, not a delivery promise. |
| D-S03.2 | Synthetic operational subledger per ADD §9.2 account groups. | Not a finance-approved chart; no legal ownership inferred. |
| D-S03.3 | Structured promotion rules; non-stacking by default; unsupported promotions ignored. Fixtures: fixed/percentage line discount, same-SKU multibuy, delivery-fee threshold, verified loyalty price. | Integer rounding; deterministic allocation of order-level discounts for refunds. |
| D-S03.4 | Postgres jobs table, `FOR UPDATE SKIP LOCKED`, lease owner/expiry, attempts, backoff, dead letter. | Queue is at-least-once; idempotency prevents duplicate effects. |
| D-S03.5 | `cryptography` AES-256-GCM behind a versioned provider interface; key from gitignored file; AAD = owner + address version. | Fictional addresses only. Not equivalent to KMS custody. |
| D-S03.6 | WebAuthn RP ID `localhost`, origin `http://localhost:8000`, page served by FastAPI; software authenticator (Chromium CDP) in tests; real verification via maintained library. | Real-device PIN and recovery remain `manual_pending`. |
| D-S03.7 | Versioned simulated provider capability profiles, including one restrictive profile; wallet fields added. | Labelled invented; live adapters inherit nothing. |
| D-S04 | Strategy names fixed as above; one-store/fewer-deliveries are option attributes. Merchant contract API authoritative; thin local merchant page/CLI harness (deliberate reduction from BP M2 portal). Wallet UI shows total/available/allocated/reserved/pending. Live credentials/endpoints refused; synthetic DB refused under live runtime. | |
| D-S05 | No float, breakage or interchange income assumed; wallet economics modelled separately. | |
| D-S06 | Fixtures use `operating_entity_demo` and fictional providers. IRONSKY role remains a founder/legal decision. | Linked to PRD open decision "Entity and IRONSKY", D01. |

## Test status taxonomy (D-S02)

Each acceptance test records scope, type, fixture, invariant, evidence artefact, limitations and one status: `passed_domain`, `passed_browser`, `passed_simulator`, `passed_environment`, `manual_pending`, `provider_pending`, `deferred_not_in_scope`, `failed`. Treatments for T03, T22, T23, T41, T43, T44, T46, T48 follow ADD §8.

---

## Implementation decisions

Record choices made during the build here, newest last, with the related D-number.

| Date | ID | Decision | Related |
|---|---|---|---|
| 2026-10-28 | I-001 | Python 3.12, dependencies pinned in `uv.lock`, uv 0.11.32 in image and CI. `httpx` kept for the test client (starlette deprecation warning accepted; replacement package not yet vetted). | D-S04 |
| 2026-10-28 | I-002 | Single-row `deployment_marker` table records environment and `synthetic=true`. Migrations refuse to create a live-marked database; app startup refuses a marker that differs from the runtime or a synthetic DB under a live runtime. | W20, D-S04 |
| 2026-10-28 | I-003 | `TROLLIE_ENV=live` refuses to start: no live adapters exist. Mandate fixture requires `TROLLIE_MANDATE_FIXTURE_ENABLED=true` and `TROLLIE_ENV=test`. | A2, D-S04 |
| 2026-10-28 | I-004 | Development tests run against a local Postgres 16; `docker compose up` is verified by a CI job, as the dev sandbox has no Docker daemon. | DoD |
| 2026-10-28 | I-005 | Added bounded contexts beyond the CLAUDE.md list: `accounts` (customers, address versions, loyalty), `merchants`, `controls` (kill switches, incidents, audit), `durable` (idempotency, outbox, inbox, jobs). | CLAUDE.md conventions |
| 2026-10-28 | I-006 | Synthetic GTINs use the GS1 restricted-circulation prefix `2` so they cannot collide with real products. All merchant and brand names are invented and labelled "(Fictional)". | CLAUDE.md scope |
| 2026-10-28 | I-007 | Redaction treats 13–19 digit runs (optionally space/dash separated) as card/ID numbers only when not adjacent to letters or digits, and never alters UUIDs. Found by a flaky test that corrupted a posting key in an incident record. | CLAUDE.md rules |
| 2026-10-28 | I-008 | Offer versions, promotions and address versions are immutable at the database level (update/delete triggers). The latest observation per location/product is current. | Blueprint §7.1 |
| 2026-10-28 | I-009 | Promotions: each line gets the single best eligible item-level promotion (ties by id); `stackable` is stored but not yet applied. Delivery thresholds use post-discount goods. Percentage discounts floor per unit. Unsupported kinds are ignored. | D-S03.3 |
| 2026-10-28 | I-010 | Quantity: a line is either an exact count of sellable units or an exact total measure; a measure is met only by one product whose packs sum exactly to it (no over-buying, no mixing pack sizes within a line). | T02, T14 |
| 2026-10-28 | I-011 | With `allow_omit_optional`, the optimiser omits only optional lines that no store can supply at all, and discloses them; it never omits an available line to lower the price. Must-have lines always block. | PRD partial rules, ADD §9.1 |
| 2026-10-28 | I-012 | Optimiser search: branch-and-bound per store set with a node budget per set; if any search exhausts its budget the strategy's options are labelled not proven optimal. Verified against a brute-force oracle (300 cases per run; 5000 with `HYPOTHESIS_PROFILE=thorough`). | T15, BP §11.4 |
| 2026-10-28 | I-013 | Estimates and firm quotes are separate immutable versions. A firm quote is derived from an estimate's snapshot (no re-optimisation) only when every leg holds a reservation for exactly those lines; the estimate becomes REPLACED. Expiry = earliest of offer validity, delivery window start and reservation expiry, minus a 2-minute execution margin. | BP §5.1, §5.5; T07 |
| 2026-10-28 | I-014 | Fulfilment mode must be chosen explicitly when firming a quote (no default); permitted omissions are allowed only in allow-partial mode and never for must-have lines. The funding source is part of the hashed snapshot. | PRD partial rules; A4 |
| 2026-10-28 | I-015 | Approval ceremony is generic over subjects (quote now, mandate in W3). Challenge TTL 5 minutes, capped at the subject's validity; user verification required (PIN or biometric); sign counter enforced; consumption and approval are atomic. | BP §13.1; A2 |
| 2026-10-28 | I-016 | External parties are simulated in `app/simulators` with their own `sim_*` tables and per-operation fault injection (`reject`, `timeout_before_effect`, `timeout_after_effect`, `lose_stock`). Trollie code sees them only through adapter contracts. | CLAUDE.md scope |
| 2026-10-28 | I-017 | Order orchestration is a set of idempotent, state-driven steps; a periodic sweep re-drives orders and refunds waiting on unresolved external state. Before acting on a payment callback the executor confirms by authoritative lookup (T30). | BP §9, §6.3 |
| 2026-10-28 | I-018 | Card branch: one final capture of the accepted total. The capture carries the allocation for the captured legs; if a profile fixes allocation at authorisation, a partial outcome fails closed (cancel and void) rather than settle the removed leg's share. | BP §9.2, §4.1; D02 |
| 2026-10-28 | I-019 | Immediate branch: payment after hold expiry pauses the order (NEEDS_ATTENTION) and tries to re-hold exactly the same lines at the same price; otherwise the whole basket is refunded. | BP §9.3; T09 |
| 2026-10-28 | I-020 | PARTIAL is a terminal order state, reported separately from COMPLETED. | BP §19.1 |
| 2026-10-28 | I-021 | Provider fees are a separate settlement line charged to the platform and are kept on refunded payments; payouts are at gross. Each provider beneficiary appears once per payment (legs sharing a courier are aggregated). | BP §14.2-14.3; T53/T54 |
| 2026-10-28 | I-022 | Refund allocation mismatch (T32): when the provider reverses part of an innocent merchant's share, Trollie posts a recovery receivable from the responsible merchant and opens a `refund_allocation_mismatch` case to make the innocent merchant whole from the reserve. | BP §2.3, §14.5 |
| 2026-10-28 | I-023 | Simulator fault consumption commits independently of the simulated action, and modes combine with `+` (e.g. `timeout_after_effect+drop_webhook`). | Test infrastructure |
| 2026-10-28 | I-024 | Wallet money operations lock the wallet row and derive balances from the ledger under that lock; there is no balance column. Wallet-funded orders create no payment operations (W16). | D-W01, D-W02 |
| 2026-10-28 | I-025 | An order has exactly one authority (DB check): a quote approval, or a mandate execution created by the trusted executor after checking every mandate condition under lock. Mandate grants activate only via the passkey ceremony bound to the grant hash. | A2 |
| 2026-10-28 | I-026 | Top-ups: credited only on a confirmed event whose transfer reference, wallet reference and amount all match an intent; wrong currency or destination is quarantined (case only); otherwise suspense plus case. Reversal freezes and returns free funds and records any shortfall as a recovery receivable. | D-W02; W01-W03, W13 |
| 2026-10-28 | I-027 | Before compensating, uncertain merchant legs are resolved by lookup; money is not released or refunded while any leg's merchant state is unknown. The reconciliation sweep isolates per-order failures. | W10, BP §9.4 |
| 2026-10-28 | I-028 | Local auth is a dev-only HMAC session token (customer or agent principal) with a generated secret; it enforces tenancy and the agent/owner split but is not a production identity system. No phone-based recovery exists. | BP §13.1, §13.3; T23, T49 |
| 2026-10-28 | I-029 | All API request schemas forbid unknown fields. Agent principals may add items, request estimates, propose preferences and submit purchase requests; approval, firm-quote, order, wallet-allocation and grant endpoints require the owner. | BP §13.2; T45, T47, T48 |
| 2026-10-28 | I-030 | The approval page is server-rendered from the immutable snapshot (seller per leg, lines, partial-fulfilment rule in words, destination label and version, windows in Africa/Johannesburg, fees, maximum total, expiry) and never shows merchant free text. | BP §13.1; PRD UX |
| 2026-10-28 | I-031 | Only one worker advances a given order at a time (Postgres advisory lock per order); a second caller returns immediately and the holder observes new state on its next step. Found by the live demo: a cancellation request and the background worker interleaved steps on one order. | BP §8.5 |
| 2026-10-28 | I-032 | The dev seed is idempotent per entity and refreshes time-bound data (offer observations, per-zone courier capacity, promotions); `/v1/dev/seed` also restocks simulated shelves while keeping holds. Dev harness only. | DoD |
| 2026-10-28 | I-033 | `scripts/demo.py` exercises the definition of done against a running server with a software passkey and pauses the background worker while it arms faults. Time-dependent cases (T08, T09, T27, T53/T54) are shown by tests with a controllable clock. | DoD |
| 2026-10-28 | I-034 | Chargebacks (simulated `dispute.opened`) are recorded as owned exposure; a refund requested while a dispute is open is held (`REFUND_HELD_DISPUTE_OPEN`) and a dispute after refunds opens a `dispute_refund_overlap` case. | T35 |
| 2026-10-28 | I-035 | `scripts/acceptance_report.py` regenerates `docs/ACCEPTANCE_STATUS.md` from a real test run; a case is shown passed only if every mapped test passed. CI runs `scripts/demo.py` against the `docker compose up` stack. | D-S02; DoD |

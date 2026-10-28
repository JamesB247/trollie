# Trollie: Wallet Scope Correction and Proposed Sprint Decisions

**Date:** 28 October 2026  
**Status:** Proposed implementation addendum for founder review; not a production approval.  
**Purpose:** Restore the agent-wallet product requirement without confusing a synthetic software build with permission to receive or hold real customer money. Answer the builder's seven review points.  
**Original files:** Unchanged. This document does not modify a repository, README, CLAUDE.md, PRD or blueprint automatically.

## 1. Decision in one paragraph

Retain customer-funded wallets and agent-specific spending accounts in Trollie's product. Add a deliberately synthetic wallet module to the current deterministic-commerce build. Implement simulated funding, customer ownership, agent allocations, spending permissions, reservations, commitment, release, refunds and reconciliation through the existing financial controls. Keep real deposits, custody, live wallet-funded purchases, withdrawals and unrestricted autonomous spending disabled until the actual legal model and provider capabilities are approved. The live pay-per-order pilot remains a possible interim route, not a replacement for the wallet vision. Whether that interim pilot launches before the wallet is a founder decision, not an assumption for the builder.

This changes the blueprint's explicit "Wallet: None" pilot baseline. It is a proposed scope change, not a claim that wallet functionality was already included. The original recommendation deferred stored value to reduce live-launch dependencies; that did not justify excluding the wallet model from all synthetic engineering. [F1, sections 1 and 3.1; F2, Phasing]

## 2. Basis, confidence and authority

### Materials actually available for this response

- **F1:** `Trollie_Engineering_Review_and_Implementation_Blueprint_2026-10-28.md`, version 1.0. Relevant sections inspected: baseline, capability contract, sample quote, optimisation, economics, acceptance tests and milestones.
- **F2:** The latest uploaded original PRD, filename ending `Architecture(3).md`; it includes the Fourth review. Its displayed version is v2, not a separately authenticated v2.1.
- **F3:** The founder's pasted builder assessment of README, CLAUDE.md, PRD v2.1 and the blueprint. The standalone README, CLAUDE.md and v2.1 files were not available in the retrieved material. Assertions about their exact wording are attributed to this assessment, not an independent repository inspection.
- **F4:** The founder's current clarification: users should be able to fund a wallet and give an agent permission to buy on their behalf.
- **S1-S6:** Primary external sources checked for the limited regulatory and technical questions in this addendum. They are listed at the end.

### Status rules

The wallet product intent is founder-stated. All detailed engineering defaults below remain **proposed** until adopted. Provider support, legal classification, accounting treatment and corporate roles are **unresolved** unless backed by their own evidence.

On adoption, record the accepted decision IDs and exact superseded clauses in DECISIONS.md. Do not apply a blanket "latest document wins" rule: a wallet scope change does not relax approval, privacy, reconciliation or money-integrity controls. Do not mark M1 complete merely because a synthetic implementation works.

## 3. Why the wallet was deferred, and what changes now

A pay-per-order service tests whether Trollie can assemble and fulfil a multi-retailer basket without also operating persistent customer balances. That was a sequencing recommendation. It was not a conclusion that wallets are impossible or commercially pointless.

The founder is describing two linked capabilities:

1. A reusable customer balance from which purchases can be funded.
2. Delegated authority allowing an agent to request purchases under explicit customer controls.

These capabilities are related, but neither implies the other. A customer can fund a wallet without authorising any purchase. An agent can have an unused spending permission while the wallet has no available funds. A virtual card is a third, separate capability: it is a payment credential, not the wallet itself.

**Proposed correction:** demonstrate all three logical layers needed now - customer balance, agent permissions and controlled purchasing - using synthetic funds. Do not add card issuing merely to build the wallet.

### Real-money boundary

The proposed non-bank payments reforms are not a general permission for Trollie to collect deposits. In the SARB Governor's 20 October 2026 address, the authorisation framework remained proposed, with publication intended by the end of November 2026. The address expressly retained governance, customer-fund safeguarding, resilience and reporting requirements for appropriately regulated non-bank participation. [S1]

For planning, therefore, classify Trollie's precise funds flow with South African payments counsel and the proposed regulated partner before accepting real top-ups. Using the word "credits" instead of "rand balance" is not evidence that a monetary product falls outside that analysis. This is a classification requirement, not a claim that every credit product has the same legal treatment.

The following are launch questions, not obstacles to writing sandbox software: who owes the customer the balance; who holds and safeguards the corresponding funds; what Trollie may instruct; applicable identity, monitoring and reporting duties; redemption and refunds; loss and insolvency allocation; settlement and reconciliation; and the effect of any new framework at activation. [S1; S2]

## 4. D-W01: Customer ownership with agent-specific spending accounts

**Proposed model:** one customer-owned wallet with explicitly allocated agent envelopes. An "agent wallet" in the user interface is a spending account within that customer relationship, not a claim that an AI is an independent legal account holder.

For the first implementation, use exclusive allocations rather than multiple agents sharing a fungible allowance. Shared access can be added later with separate concurrency semantics.

### Example

A simulated R2,000 top-up produces a R2,000 customer balance. The owner allocates R1,500 to the grocery agent and leaves R500 unallocated. Allocating funds does not create another R1,500.

The grocery agent requests the blueprint's R1,100 basket: R600 goods at Store A, R400 at Store B, two R40 delivery charges and a R20 service fee. [F1, section 10.4]

| State | Owner unallocated | Grocery available | Purchase reserved | Total remaining customer balance |
|---|---:|---:|---:|---:|
| Top-up confirmed | R2,000 | R0 | R0 | R2,000 |
| R1,500 allocated | R500 | R1,500 | R0 | R2,000 |
| Approved R1,100 reserved | R500 | R400 | R1,100 | R2,000 |
| Purchase commitment posted | R500 | R400 | R0 | R900 |

The final row also creates obligations to the recipients; it does not establish that they have already received settlement. A reservation cancellation before commitment restores the grocery envelope, once the system establishes that no conflicting commitment occurred.

Pending top-ups, disputed funds and expected refunds are not automatically spendable. Display them separately. Customer aggregate totals must not double-count parent and envelope balances.

### Minimum domain objects

`wallet`, `wallet_envelope`, `agent_grant`, `funding_intent`, `funding_event`, `wallet_reservation`, `wallet_commitment`, `refund_obligation`, `redemption_request`, `financial_operation` and references into the existing ledger, inbox and outbox.

Each financial object must carry owner, environment, currency, immutable business-operation reference and relevant quote/grant versions. Use integer minor units. The simulator is denominated in ZAR for realistic arithmetic but visibly labelled **SIMULATED - NOT REAL MONEY**.

## 5. D-W02: Funding and spending are separate workflows

### Funding

A top-up request creates an intent. Only sufficiently authoritative provider evidence under the selected capability profile can establish funds available for use. In this sprint, that evidence comes from the simulator.

A pending bank transfer, browser return, screenshot, email, claimed payment, or arbitrary webhook body is not sufficient. Validate authenticity, destination account, environment, currency, amount and event identity. Apply the defined provider lookup/reconciliation policy. An authenticated notification can still require confirmation of what financial state it represents.

Unmatched inbound funds belong in a non-spendable suspense workflow, not the nearest user's balance. Duplicate evidence for one economic credit must post once. Unexpected overpayments or different amounts require reconciliation rather than silent matching.

### Purchasing

The sequence for a wallet-funded purchase is:

1. Build the same authoritative, fulfilable quote used by pay-per-order commerce.
2. Obtain explicit purchase approval or match an already approved, applicable standing mandate.
3. Atomically check wallet availability, envelope allocation, grant limits, reservations, revocation and applicable aggregate/velocity limits.
4. Reserve the allowed amount while coordinating merchant preparation under the agreed workflow.
5. Commit the actual permitted purchase amount and create the corresponding merchant/courier/platform obligations; release unused reservation only when safe.
6. Reconcile external settlement independently. A local wallet debit is not proof of recipient settlement.

Do not run a new customer pay-in for an already funded wallet purchase. Do not disguise a wallet reservation as a bank-card authorisation. Retain separate adapters or funding-source implementations for pay-per-order and wallet-funded purchases while reusing quote, authority, ledger and fulfilment controls.

Unknown external state must not result in both released customer funds and a potentially committed merchant payment. Freeze the affected amount, reconcile and expose an honest pending status.

### Refunds and redemption

A refund creates an entitlement and a workflow, not an unrestricted balance edit. Before commitment, cancellation releases a reservation. After commitment, reversing the purchase and funding the refund require separate accounting and external evidence.

For a wallet-funded purchase, restoration to the original wallet can be an appropriate designed path, subject to the adopted legal/partner model and customer rights. A pay-per-order refund must not be forced into wallet credit. Keep withdrawal/redemption separate from purchase refunds.

Do not spend another customer's money to bridge a refund. Any discretionary early credit must have an explicit funded platform-reserve entry and recovery/loss treatment. Repeated refund requests must not create repeated credits.

## 6. D-W03: Delegated authority and autonomy

**Normal sandbox journey:** explicit, quote-bound passkey approval for each purchase, as in the existing blueprint.

**Separate synthetic mandate scenario:** include a bounded test mode demonstrating that an agent can purchase without a fresh approval for every basket when the owner has already approved an adequate mandate. This is not enabled by depositing money or setting an account balance.

The grant/mandate record contains customer and agent identity, permitted envelope, category or exact-item constraints, merchant set, address version, per-order cap, cumulative period cap, velocity limit, start/end times, purpose, substitution rules, approval mode, version and revocation state.

Use a fixed test clock and Africa/Johannesburg business-time interpretation; store instants in UTC. A period reset must not lose outstanding reservations. Refunds do not automatically replenish spending velocity or cumulative authorisation limits: default to no automatic restoration of those limits, while restoring money through the correct refund process.

Only the owner can broaden a grant. An agent cannot allocate more funds to itself, alter its cap, change the destination or revoke someone else's controls. The trusted execution service evaluates authority; the agent may request execution but cannot sign customer consent or make ledger postings.

At revocation, stop new unauthorised financial commitments. Already incurred merchant obligations, reconciliation and legitimate refund processing still continue. Do not promise that revocation can reverse an external payment already executed.

This wallet/mandate work is an explicit scope addition. Do not hide it within an unchanged M2-M3 estimate or treat it as a production-ready autonomous agent integration.

## 7. D-S01: Correct the milestone statement

Use the scope label:

> **M0 baseline work + M2-M3 synthetic commerce build + W1-W3 synthetic wallet extension. M1 commercial feasibility remains open.**

M0 is not automatically complete when a file named DECISIONS.md exists. Its exit evidence is an adopted baseline, owners, unresolved decisions and traceability. M1 includes commercial/provider/courier evidence and cannot be fulfilled through code. The blueprint separately identifies M2 commerce and M3 authority/durable operations. [F1, section 18]

Synthetic engineering can proceed in parallel with M1. No live commerce, whether human-assisted or automated, bypasses the applicable legal, provider and operational gates.

| Added work package | Proposed exit evidence |
|---|---|
| W1 - Funding and ownership | Simulated inbound funding, suspense, exclusive envelopes and ownership invariants |
| W2 - Controlled wallet purchases | Reserve/commit/release/refund/redemption-state tests with the existing quote and orchestration engine |
| W3 - Delegation and fault recovery | Bounded mandate fixture, concurrent-agent tests, revocation, top-up reversal and crash recovery |

## 8. D-S02: Resolve the test-list mismatch

The builder is correct that excluding T31-T44 while claiming full compensation coverage is inconsistent. The blueprint includes provider limitations, targeted refunds, refund races, chargebacks, payout failures, capture/cancellation races and delivery failures in that range. [F1, section 17]

**Proposed requirement:** retain the existing applicable tests, add **all T31-T40 as simulator/domain tests**, and cover T42's approved-address rule. This is more complete than adding only T31, T33, T34 and T37-T40. T32, T35 and T36 are particularly relevant once customer balances exist.

For every test, record implementation scope, test type, fixture, expected invariant, evidence artifact and limitations. Use distinct statuses: `passed_domain`, `passed_browser`, `passed_simulator`, `passed_environment`, `manual_pending`, `provider_pending`, `deferred_not_in_scope`, or `failed`. A boundary-level test is not a claim of full end-to-end validation.

### Specific exceptions raised by the builder

| Test | Proposed treatment now | What remains unproven |
|---|---|---|
| T03 - shelf-photo uncertainty | Supply a fabricated extraction result and prove that an unconfirmed match cannot become orderable | Real camera/OCR extraction accuracy |
| T22 - PIN-supported authenticator | Test user-verification success/failure using a virtual authenticator; do not require Face ID or inspect raw biometrics | Actual PIN-only device usability and recovery |
| T23 - recycled number recovery | No phone-based recovery endpoint or silent reassignment; negative boundary tests only | A complete real recovery journey |
| T46 - malicious egress | No arbitrary fetch tool; deny outbound runtime network access in the sandbox and verify it in an environment test | Production cloud egress policy/certification |
| T48 - poisoned preference | Inject an untrusted proposed preference; reject unconfirmed promotion or overwrite | Robustness of a real model across languages and prompts |
| T41 - consolidated pickup failure | Reject consolidation when capability disabled; a fixture may exercise the failure contract | Real multi-pickup courier behaviour |
| T42 - alternate delivery address | Mandatory domain test: no redirect without appropriate fresh authority | Real courier compliance |
| T43-T44 - damaged goods and recalls | Preserve order/product traceability; simulate applicable refund/control transitions if those operations are implemented | Operational evidence handling, recalls and real liability allocation |

WebAuthn supports user verification through methods including PIN and biometrics. A virtual authenticator can test protocol behaviour; it does not prove that a real user completed a PIN flow on a physical device. [S3; S4]

The remainder of T55-T60 needs the same honest classification. Do not introduce WhatsApp, real language models or real customer data merely to turn a test checklist green. Conversely, financial-reserve checks and supported-catalogue coverage can be tested synthetically now.

### Wallet-specific acceptance catalogue

| ID | Scenario | Required invariant |
|---|---|---|
| W01 | Duplicate confirmed top-up event | One economic credit, including through different retry paths |
| W02 | Top-up pending, failed or unverified | No spendable customer credit |
| W03 | Wrong currency, environment, destination or unmatched reference | Quarantine/suspense; no guessed wallet allocation |
| W04 | Concurrent allocation of the same owner funds | Exclusive envelopes cannot exceed available owner funds |
| W05 | Two agents reserve simultaneously | Atomic limits; no overspending or double-use of balance |
| W06 | Funds exist but grant/approval is absent | Purchase refused |
| W07 | Grant exists but funds are insufficient | Purchase refused; no unintended overdraft |
| W08 | Agent tries to broaden scope or redirect payee/address | Rejected and audited |
| W09 | Agent revoked between request and financial commitment | New commitment stops under current grant state; incurred obligations preserved |
| W10 | Cancellation or timeout after uncertain merchant action | Do not release money until safe; reconcile before retry |
| W11 | Reservation release delivered twice | Money restored once, not twice |
| W12 | Partial refunds race or repeat | Total customer credit never exceeds authorised entitlement |
| W13 | Confirmed top-up later disputed/reversed | Freeze affected exposure and record recovery/loss; do not erase history or debit other customers |
| W14 | Redemption races purchase | The same available amount cannot both leave the wallet and fund the basket |
| W15 | Repeated small requests evade per-order cap | Aggregate and velocity limits still stop excess spending |
| W16 | Wallet-funded purchase executes | No second external debit of the customer's funding source |
| W17 | Operating funds and customer balances | Separate accounting identities; no silent cross-customer subsidy |
| W18 | Refund near mandate-period boundary | Money and authorisation counters remain distinct and correct |
| W19 | Crash after external result but before local completion | Reconciliation produces one economic effect; no blind replacement operation |
| W20 | Restart with synthetic database under live configuration | Startup refuses; no conversion of demo credit to real value |

## 9. D-S03: Explicit defaults for the seven day-one decisions

### 9.1 Balanced strategy

Use versioned synthetic defaults, not claims about real Johannesburg service times:

- Maximum two retailers and two separate delivery legs; consolidation disabled by default.
- All hard quantity, product, authority, cost and customer-deadline constraints apply first.
- `cheapest`: minimise delivered customer total among feasible candidates.
- `fastest_complete`: minimise the end of the latest promised delivery window needed to fulfil the agreed basket; break ties by delivered total.
- `balanced`: calculate the fastest feasible whole-basket completion `t_fastest`, then minimise delivered total among candidates finishing by `min(customer_deadline, t_fastest + 30 minutes)`.
- Show the 30-minute policy in the UI and quote policy version; it is a proposed simulation default, not an invisible customer rule or live delivery guarantee.
- Remaining ties: fewer delivery legs, then earlier whole-basket completion, then stable offer identifiers.

Use explicit fixture deadlines. For an interactive session without a required deadline, ask for it or obtain acceptance of a displayed default; do not invent a binding promise. Unavailable must-have items block commitment. Optional omissions must follow the approved omission policy, not silently manufacture a cheap empty basket. A solver timeout must not be labelled a proven optimum. [F1, section 11]

### 9.2 Synthetic chart of accounts

Create a documented operational subledger for the simulator, **not a claimed finance-approved statutory chart**. The real partner model determines who recognises assets and liabilities. No inference that Trollie legally owns safeguarded customer assets follows from this test model.

| Account group | Purpose |
|---|---|
| Simulated external funds control | Counterpart to funds confirmed by the simulated provider |
| Customer unallocated liability | Owner funds not allocated to an agent envelope |
| Customer envelope-available liability | Exclusive funds available to a particular delegated account |
| Customer purchase-reserved liability | Amount unavailable to other spending while a purchase is pending |
| Customer redemption payable | Funds reserved for an approved outbound redemption |
| Unmatched inbound suspense | Confirmed receipt whose ownership or allocation is not established |
| Merchant payable | Amount owed to a named seller |
| Courier payable | Amount owed to a named courier |
| Platform fee clearing | Fee awaiting its defined recognition/settlement treatment |
| Refund recovery receivable / funded compensation | Explicit treatment for early refund funding after merchant settlement |
| Operating-reserve control | Separately identified platform-funded reserve, never another customer's balance |

Use the same authoritative ledger rather than a second mutable wallet balance system. Journals are immutable and balanced per currency/environment. Lock the relevant control rows, validate ownership and available balances, post entries and create outbox records in one database transaction. An asynchronous worker must not be able to bypass these checks. Disallow direct balance editing by API, agent and support roles.

Example journals in rand, for explanation only:

- Confirm top-up: debit simulated external funds control R2,000; credit customer unallocated liability R2,000.
- Allocate: debit unallocated R1,500; credit grocery-available R1,500.
- Reserve: debit grocery-available R1,100; credit purchase-reserved R1,100.
- Commit approved example: debit reserved R1,100; credit Store A payable R600, Store B payable R400, courier payable R80, platform fee clearing R20.
- A pre-commit cancellation reverses the reservation transfer, once commitment is ruled out. It does not reverse the original top-up.

Post-commit refunds depend on whether payables remain unsettled or recovery is needed. They need explicit event templates; do not reuse a reservation-release journal. The R20 clearing entry is not a declaration of tax treatment or earned revenue.

### 9.3 Promotions

Use deterministic structured rules: merchant/location, validity interval, eligible product IDs, quantity/minimum-spend conditions, eligible customer segment, loyalty entitlement, benefit amount, cap, stacking policy and version. No free-text promotion interpreted by the optimiser or model.

Initial fixtures: fixed/percentage line discount, fixed-price same-SKU multibuy, delivery-fee threshold and verified loyalty-only price. Default non-stacking unless a fixture explicitly permits it. Ignore unsupported promotions rather than invent a discount. Evaluate seller-specific delivery thresholds on the defined pre/post-discount amount in that merchant's rule. Specify integer rounding and allocate order-level discounts deterministically for partial refunds.

T11 is specifically about delivery-threshold effects on store splitting, not solely merchandise promotion. T12 covers ineligible loyalty membership. Both must have known-answer fixtures. [F1, section 17]

### 9.4 Queue

Use a Postgres-backed jobs table for this local sprint. `FOR UPDATE SKIP LOCKED` is documented as useful for queue-like tables with multiple consumers, but is not a general consistency mechanism. [S5]

Claim jobs in a short transaction; persist lease owner/expiry and commit. Process outside that transaction; acknowledge with the lease token. Include attempts, available-at time, backoff, dead-letter state and observable reconciliation. Workers may run more than once. Financial idempotency and valid state transitions, not the queue, prevent duplicate economic effects. Preserve business-operation ordering where required.

### 9.5 Local address encryption

Use a versioned encryption-provider interface, with a generated local-development key injected from a gitignored secret file/mount. Use the maintained cryptography library's authenticated-encryption implementation, such as AES-256-GCM, with unique nonces, key IDs and authenticated owner/address-version context. Never write an algorithm or embed a reusable key in the repository. The library documents nonce-reuse hazards. [S6]

Only fictional addresses are permitted now. Reject unexpected key versions and wrong-context decryptions. Real KMS integration and production key lifecycle stay outside this sprint; local encryption is not claimed equivalent to production key custody.

### 9.6 WebAuthn

Use `localhost` as the local RP ID, with one explicitly configured exact browser origin, for example `http://localhost:8000`. Port is part of the origin, not the RP ID. Chromium documents the localhost HTTP exception; a Docker hostname or a phone accessing an arbitrary LAN IP is not automatically equivalent. [S3; S4]

Serve the minimal approval page from FastAPI for this sprint. Use a software authenticator in automated browser tests and validate actual assertions, challenge consumption, origin, RP ID, user ownership and user-verification flags. Do not stub the server to accept every assertion. Fake funds do not justify fake security verification.

Physical-device PIN-only and recovery testing remain explicit manual/real-device evidence requirements. No need to implement Next.js or a native application to test the approval contract.

### 9.7 Provider capability profiles

Implement versioned fake profiles now. Include one intentionally restrictive profile to prove that unsupported combinations fail closed.

Profiles distinguish supported currency, collection semantics, capture counts, recipient count, settlement timing, partial refunds and allocation behaviour, status lookup, idempotency retention, webhook signatures and settlement reports. These fields are already required by the blueprint. [F1, section 4.1]

Add wallet-related fields for permitted stored-value activity, custodian/issuer role, top-up evidence, redemption, restrictions/freezes, funding reversals and customer-balance reporting. For the simulator, these are invented capabilities labelled as such. A live adapter cannot inherit permission from a fake profile.

## 10. D-S04: Resolve the small inconsistencies without widening the stack

- The three strategies are `cheapest`, `fastest_complete`, `balanced`. One-store/two-store and fewer-deliveries are option attributes/comparators, not competing strategy names.
- The merchant contract API is authoritative. Add a thin local merchant page or a documented signed-in command-line harness to demonstrate acceptance/rejection and ready-for-collection transitions. Record this as a deliberate reduction from the full portal in blueprint M2, not delivery of that portal.
- Retain Python 3.12, FastAPI and Postgres for the local sprint as reported by the builder. Pin actual versions/dependencies during implementation. No Redis, AWS, Next.js, WhatsApp, production LLM or real merchant integration is required for these synthetic tests.
- Add a small wallet UI showing simulated total, available, allocated, reserved and pending amounts; owner allocation, agent scope, revocation and funding status. It must not display pending funds as usable.
- Runtime adapters must be local fixtures only. An environment flag alone is not sufficient separation: refuse live credentials/endpoints and refuse a synthetic database in a live runtime. No public unauthenticated credit-wallet endpoint.

## 11. D-S05: Numerical checks and wallet economics

The builder's quoted arithmetic matches the blueprint: the sample basket is R1,100; the one-store illustrative model gives R32.21 contribution on R2,000 goods at 5% commission, minus R2.79 after an additional R35 subsidy, and R628.24 break-even goods value. These are model outputs, not partner quotations or evidence of viability. [F1, sections 10.4 and 16.1]

Adding wallets requires a revised model. Measure funding costs, balance-servicing and partner fees, unused/refunded funding, redemption, compliance operations, chargebacks/fraud, reconciliation, reserve funding and customer support. Do not treat wallet top-ups as sales or customer balances as operating revenue. Do not assume that fewer pay-ins remove percentage-based fees: at an illustrative 1.5%, one R2,000 funding event and four R500 events both incur R30 before fixed or other fees.

The proposed model has no assumed float income, breakage revenue or interchange revenue. Any entitlement requires the actual legal and commercial arrangement. Wallet UX value and wallet economics must be measured separately.

## 12. D-S06: IRONSKY remains a founder/legal decision

Do not assign a real legal entity, bank account, merchant counterparty or wallet issuer based on the builder's guess. In fixtures, use `operating_entity_demo` and fictional providers.

Before real contracts, record the legal entity that contracts with customers, merchants and payment providers; who owns/has rights to the software; whether IRONSKY supplies technology/security services or operates Trollie; who owes customer balances; who receives fees; and responsibility for complaints and losses.

A separate Trollie operating entity with IRONSKY as a contracted technology/security supplier is an option to evaluate, not an approved structure or a claim that group liability automatically disappears.

## 13. Definition of done for the revised synthetic build

The end-to-end evidence must demonstrate the following without external live services:

1. Local startup with pinned dependencies, migrations and fictional seed data.
2. A customer funds a simulated wallet; a duplicate event does not double-credit it.
3. The customer allocates an exclusive agent envelope and approves its scoped grant.
4. An agent fixture proposes a two-store basket; the server produces an immutable quote.
5. The owner approves through a real WebAuthn ceremony against a software authenticator, or the separate bounded-mandate fixture supplies valid prior authority.
6. Wallet funds are reserved, merchant responses simulated, the allowed purchase committed, delivery simulated and settlement reconciled.
7. Re-run with a merchant refusal, top-up mismatch, expired reservation, unknown settlement, cancellation race, duplicate webhook and two concurrent agents. Each yields the expected control and compensation outcome.
8. Postgres restarts and worker crashes do not manufacture funds or discard obligations. Customer and recipient positions reconcile; every posted journal remains balanced.
9. Test output distinguishes simulated/domain/browser evidence from outstanding real-provider, real-device and operational evidence.

The sandbox proves implementation behaviour under stated fixtures. It does not prove external provider capabilities, production readiness, real delivery performance, legal authorisation or commercial demand.

## 14. Instruction to give the builder

> Keep the wallet as a core Trollie product capability. Revise the current sprint to M0 documentation plus M2-M3 synthetic commerce and a separately identified W1-W3 synthetic wallet extension. Do not represent M1 commercial feasibility as complete.
>
> Implement customer-owned simulated ZAR wallets with agent-specific exclusive allocations, scoped revocable spending grants, pending/confirmed funding, atomic reservations, commitment, release, refunds, redemption state and reconciliation. Reuse the authoritative ledger and purchase controls. Do not build a parallel editable balance system or charge the customer again when spending funded balance.
>
> Keep real deposits, real merchants, live payouts, actual card issuing, WhatsApp, real LLM calls and external agents out of this sprint. Wallet funding is not purchase consent. Keep quote-bound approval in the normal flow; add a separately flagged bounded-mandate fixture for autonomy tests.
>
> Add T31-T40, the approved-address control and W01-W20. Map other tests to domain, browser, simulator, environment, manual or future-provider evidence honestly. Do not claim OCR, real PIN-device behaviour or production egress is proven by a fixture.
>
> Use this document's defaults only after marking the chosen decisions adopted in DECISIONS.md and recording superseded clauses. Update README, CLAUDE.md and the PRD consistently before continuing. Preserve already implemented commerce, security and reconciliation modules; do not restart the codebase unnecessarily. Report scope additions and unvalidated assumptions explicitly.

## Primary-source register

Checked 28 October 2026. This is a limited verification for the present scope decision, not a fresh audit of every legal/statistical assertion in earlier drafts.

- **S1 - SARB, Governor's address, 20 October 2026, Rewiring Payments: Open. Connected. Inclusive.** Proposed non-bank framework, safeguards and intended end-November publication. `https://www.resbank.co.za/en/home/publications/publication-detail-pages/speeches/speeches-by-governors/2026/kganyago-payments-conference`
- **S2 - SARB, Regulation.** NPS regulatory instruments, distinction between directives and position papers, and current registration/authorisation material. `https://www.resbank.co.za/en/home/what-we-do/payments-and-settlements/regulation`
- **S3 - W3C, Web Authentication Level 3; Chromium origin rules.** User verification and local origin/RP constraints. `https://www.w3.org/TR/webauthn-3/` and `https://chromium.googlesource.com/chromium/src/+/refs/heads/main/content/browser/webauth/origins.md`
- **S4 - Chrome DevTools, Emulate authenticators; WebAuthn protocol domain.** Virtual authenticator facilities and simulated user verification. `https://developer.chrome.com/docs/devtools/webauthn/` and `https://chromedevtools.github.io/devtools-protocol/tot/WebAuthn/`
- **S5 - PostgreSQL 18, SELECT reference.** Queue-like use and limitations of SKIP LOCKED. `https://www.postgresql.org/docs/18/sql-select.html`
- **S6 - Python cryptography, Authenticated encryption.** Maintained AEAD implementations, authenticated context and nonce-reuse warnings. Use a supported pinned release at implementation rather than copying a development-version requirement. `https://cryptography.io/en/latest/hazmat/primitives/aead/`

## Document validation

The arithmetic examples and test-ID integrity are mechanically checked when this file is generated. This does not mean any application test has been executed. No codebase, partner account or legal approval was changed by producing this addendum.
